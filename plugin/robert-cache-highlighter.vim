" ============================================================================
" Robert Cache Highlighter - Show Previously Looked-up Words
" ============================================================================
"
" Highlights all words/phrases from your lookup cache so you can see
" which vocabulary you've already studied.
"
" Features:
"   - Reads from ~/.cache/robert-online/cache.csv (persistent cache)
"   - Tracks words looked up in current session (in-memory)
"   - Automatically integrates with selection-grep.vim (,, keybinding)
"   - Highlights both single words and multi-word phrases
"   - Subtle visual style that doesn't interfere with reading
"   - Works independently or alongside Reader Mode
"
" Commands:
"   :ReaderShowCached     - Highlight all cached words
"   :ReaderHideCached     - Remove cache highlights
"   :ReaderToggleCached   - Toggle cache highlighting
"   :ReaderReloadCache    - Reload cache from CSV file
"   :ReaderCacheStats     - Show cache statistics
"   :RobertClearSession   - Clear in-memory session words
"
" Keybindings:
"   <leader>rs - Toggle cache highlighting
"
" Integration:
"   When you press ,, to look up a word, it's automatically added to the
"   session word list and highlighted (if cache highlighting is enabled).
"
" ============================================================================

" ============================================================================
" Configuration
" ============================================================================

let g:robert_cache_enabled = 0
let g:robert_cache_file = expand('~/.cache/robert-online/cache.csv')
let g:robert_cache_highlight_style = get(g:, 'robert_cache_highlight_style', 'underline')
let s:cached_words = []
let s:cache_loaded = 0

" In-memory tracking of lookups in current session
if !exists('g:robert_session_words')
    let g:robert_session_words = []
endif

" ============================================================================
" Cache Loading
" ============================================================================

function! s:LoadCacheWords()
    " Only load once per session
    if s:cache_loaded
        return
    endif
    
    if !filereadable(g:robert_cache_file)
        " Create empty cache file with CSV header
        let cache_dir = fnamemodify(g:robert_cache_file, ':h')
        if !isdirectory(cache_dir)
            call mkdir(cache_dir, 'p')
        endif
        call writefile(['key,context,result_json'], g:robert_cache_file)
        echo '✓ Created empty cache file: ' . g:robert_cache_file
    endif
    
    let s:cached_words = []
    let lines = readfile(g:robert_cache_file)
    
    " Skip header line
    if len(lines) > 1
        for line in lines[1:]
            " Parse CSV: first field is the key
            let key = s:ParseCSVFirstField(line)
            
            if key == ''
                continue
            endif
            
            " Handle context keys (format: "word||phrase")
            if key =~ '||'
                let word = split(key, '||')[0]
                " Debug: show what we're extracting
                if exists('g:robert_debug_loading')
                    echom 'Extracted from context key: "' . word . '"'
                endif
                call add(s:cached_words, word)
            else
                " Simple key - just the word
                if exists('g:robert_debug_loading')
                    echom 'Simple key: "' . key . '"'
                endif
                call add(s:cached_words, key)
            endif
        endfor
    endif
    
    " Remove duplicates and sort by length (longest first for better matching)
    let s:cached_words = uniq(sort(s:cached_words))
    let s:cached_words = reverse(sort(s:cached_words, function('s:CompareLength')))
    
    let s:cache_loaded = 1
    echo '📚 Loaded ' . len(s:cached_words) . ' cached words'
    
    if exists('g:robert_debug_loading')
        " Show first 10 words including multi-word phrases
        let sample = []
        for word in s:cached_words[0:min([9, len(s:cached_words)-1])]
            if word =~ '\s'
                call add(sample, '"' . word . '" (multi-word)')
            else
                call add(sample, word)
            endif
        endfor
        echom 'Sample: ' . join(sample, ', ')
    endif
endfunction

function! s:ParseCSVFirstField(line)
    " Simple CSV parser for first field
    " Handles quoted fields with commas inside
    let line = a:line
    
    if len(line) == 0
        return ''
    endif
    
    if line[0] == '"'
        " Quoted field - find closing quote (not followed by another quote)
        let pos = 1
        let result = ''
        while pos < len(line)
            if line[pos] == '"'
                if pos + 1 < len(line) && line[pos + 1] == '"'
                    " Escaped quote - add one quote and skip both
                    let result .= '"'
                    let pos += 2
                else
                    " End of quoted field
                    return result
                endif
            else
                let result .= line[pos]
                let pos += 1
            endif
        endwhile
        return result
    else
        " Unquoted field - find first comma
        let end = match(line, ',')
        if end > 0
            return line[0:end-1]
        endif
    endif
    
    return ''
endfunction

function! s:CompareLength(word1, word2)
    " Sort by length (for reverse sort to get longest first)
    return len(a:word1) - len(a:word2)
endfunction

" ============================================================================
" Highlighting Functions
" ============================================================================

function! s:SetupHighlightStyle()
    " Define highlight style for cached words
    if g:robert_cache_highlight_style == 'underline'
        " Subtle underline
        highlight RobertCached gui=underline guisp=#6A9955 cterm=underline ctermfg=108
    elseif g:robert_cache_highlight_style == 'background'
        " Subtle background tint
        highlight RobertCached guibg=#2A3A2A guifg=NONE ctermbg=236 ctermfg=NONE
    elseif g:robert_cache_highlight_style == 'dim'
        " Slightly dimmed text
        highlight RobertCached guifg=#7A8A7A gui=NONE ctermfg=246 cterm=NONE
    elseif g:robert_cache_highlight_style == 'bold'
        " Bold text
        highlight RobertCached gui=bold cterm=bold
    else
        " Default: subtle underline
        highlight RobertCached gui=underline guisp=#6A9955 cterm=underline ctermfg=108
    endif
endfunction

function! s:ApplyCacheHighlights()
    if !s:cache_loaded
        call s:LoadCacheWords()
    endif
    
    " Combine cached words and session words
    let all_words = s:cached_words + g:robert_session_words
    
    if len(all_words) == 0
        echo '📚 No cached words to highlight'
        return
    endif
    
    " Remove duplicates and sort by length (longest first)
    let all_words = uniq(sort(all_words))
    let all_words = reverse(sort(all_words, function('s:CompareLength')))
    
    " Clear any existing highlights
    call s:ClearCacheHighlights()
    
    " Setup highlight style
    call s:SetupHighlightStyle()
    
    " Store match IDs for later removal
    let w:robert_cache_matches = []
    
    " Highlight each cached word/phrase
    let success_count = 0
    let fail_count = 0
    
    for word in all_words
        try
            " Clean the word (remove trailing punctuation for better matching)
            let clean_word = substitute(word, '[,;:.!?]\+$', '', '')
            
            if clean_word == ''
                continue
            endif
            
            " For single words without spaces or special chars, use word boundaries
            " For multi-word phrases, use literal matching with very nomagic mode
            if clean_word !~ '\s' && clean_word !~ "['/()]"
                " Single word - use word boundaries with case-insensitive flag
                " Escape special regex characters but not apostrophes in word boundaries
                let pattern = '\c\<' . escape(clean_word, '\.*^$[]~&') . '\>'
            else
                " Multi-word phrase or word with special chars - use very nomagic mode
                " Add \c for case-insensitive matching (must come before \V)
                let pattern = '\c\V' . escape(clean_word, '\')
                " Debug multi-word patterns
                if exists('g:robert_debug_highlights')
                    echom 'Multi-word: "' . clean_word . '" -> pattern: ' . pattern
                endif
            endif
            
            " Add match with priority 2 (lower than Reader Mode highlights at 5-10)
            let match_id = matchadd('RobertCached', pattern, 2)
            call add(w:robert_cache_matches, match_id)
            let success_count += 1
        catch /^Vim\%((\a\+)\)\=:E/
            let fail_count += 1
            " Debug: uncomment to see which patterns fail
            if exists('g:robert_debug_highlights')
                echom 'Failed to highlight: "' . word . '" - Error: ' . v:exception
            endif
            continue
        endtry
    endfor
    
    if exists('g:robert_debug_highlights')
        echom 'Highlight results: ' . success_count . ' succeeded, ' . fail_count . ' failed'
    endif
    
    let cached_count = len(s:cached_words)
    let session_count = len(g:robert_session_words)
    echo '✨ Highlighted ' . cached_count . ' cached + ' . session_count . ' session words'
endfunction

function! s:ClearCacheHighlights()
    if exists('w:robert_cache_matches')
        for match_id in w:robert_cache_matches
            silent! call matchdelete(match_id)
        endfor
        unlet w:robert_cache_matches
    endif
endfunction

function! s:EscapeForRegex(text)
    " Escape special regex characters for Vim's very magic mode
    " Use \V (very nomagic) mode where only backslash is special
    let text = escape(a:text, '\')
    return '\V' . text
endfunction

" ============================================================================
" In-Memory Tracking
" ============================================================================

function! RobertAddSessionWord(word)
    " Add word to session tracking and highlight it immediately
    let word = a:word
    
    " Don't add if already in list
    if index(g:robert_session_words, word) >= 0
        return
    endif
    
    call add(g:robert_session_words, word)
    
    " If cache highlighting is enabled, refresh all highlights
    if g:robert_cache_enabled
        call s:ApplyCacheHighlights()
    else
        " Even if cache highlighting isn't enabled, add this word's highlight immediately
        call s:HighlightSingleWord(word)
    endif
endfunction

function! s:HighlightSingleWord(word)
    " Highlight a single word immediately in current window
    " Initialize if needed
    if !exists('w:robert_cache_matches')
        let w:robert_cache_matches = []
    endif
    
    " Setup highlight style
    call s:SetupHighlightStyle()
    
    try
        " Clean the word
        let clean_word = substitute(a:word, '[,;:.!?]\+$', '', '')
        
        if clean_word == ''
            return
        endif
        
        " Create pattern - same logic as ApplyCacheHighlights (with case-insensitive)
        if clean_word !~ '\s' && clean_word !~ "['/()]"
            let pattern = '\c\<' . escape(clean_word, '\.*^$[]~&') . '\>'
        else
            let pattern = '\c\V' . escape(clean_word, '\')
        endif
        
        " Add match
        let match_id = matchadd('RobertCached', pattern, 2)
        call add(w:robert_cache_matches, match_id)
    catch
        " Debug: uncomment to see errors
        " echom 'Failed to highlight: ' . a:word . ' - Error: ' . v:exception
    endtry
endfunction

function! RobertClearSessionWords()
    " Clear in-memory session words
    let g:robert_session_words = []
    
    if g:robert_cache_enabled
        call s:ApplyCacheHighlights()
    endif
    
    echo '🗑️  Cleared ' . len(g:robert_session_words) . ' session words'
endfunction

" ============================================================================
" Public API
" ============================================================================

function! RobertShowCached()
    let g:robert_cache_enabled = 1
    call s:ApplyCacheHighlights()
    
    " Setup autocmd to apply highlights to new windows
    augroup RobertCacheHighlighter
        autocmd!
        autocmd BufWinEnter * call s:ApplyCacheHighlights()
        autocmd ColorScheme * call s:SetupHighlightStyle()
    augroup END
endfunction

function! RobertHideCached()
    let g:robert_cache_enabled = 0
    
    " Clear autocmds
    augroup RobertCacheHighlighter
        autocmd!
    augroup END
    
    " Clear highlights in current window
    call s:ClearCacheHighlights()
    
    echo '📚 Cache highlighting disabled'
endfunction

function! RobertToggleCached()
    if g:robert_cache_enabled
        call RobertHideCached()
    else
        call RobertShowCached()
    endif
endfunction

function! RobertReloadCache()
    " Force reload of cache (useful after looking up new words)
    let s:cache_loaded = 0
    let s:cached_words = []
    
    if g:robert_cache_enabled
        call s:ApplyCacheHighlights()
    else
        echo '📚 Cache reloaded. Use :ReaderShowCached to highlight.'
    endif
endfunction

" ============================================================================
" Cache Statistics
" ============================================================================

function! RobertCacheStats()
    if !s:cache_loaded
        call s:LoadCacheWords()
    endif
    
    echo '📊 Cache Statistics:'
    echo '  Cached words (persistent): ' . len(s:cached_words)
    echo '  Session words (in-memory): ' . len(g:robert_session_words)
    echo '  Total: ' . (len(s:cached_words) + len(g:robert_session_words))
    
    " Count multi-word phrases in cache
    let phrase_count = 0
    let single_word_count = 0
    for word in s:cached_words
        if word =~ '\s'
            let phrase_count += 1
        else
            let single_word_count += 1
        endif
    endfor
    
    echo '  Single words: ' . single_word_count
    echo '  Multi-word phrases: ' . phrase_count
    echo '  Cache file: ' . g:robert_cache_file
    
    " Show sample of cached words
    if len(s:cached_words) > 0
        echo '  Sample cached: ' . join(s:cached_words[0:min([4, len(s:cached_words)-1])], ', ')
    endif
    
    " Show session words
    if len(g:robert_session_words) > 0
        echo '  Session words: ' . join(g:robert_session_words, ', ')
    endif
endfunction

" ============================================================================
" Commands
" ============================================================================

command! ReaderShowCached call RobertShowCached()
command! ReaderHideCached call RobertHideCached()
command! ReaderToggleCached call RobertToggleCached()
command! ReaderReloadCache call RobertReloadCache()
command! ReaderCacheStats call RobertCacheStats()
command! -nargs=1 RobertAddWord call RobertAddSessionWord(<q-args>)
command! RobertClearSession call RobertClearSessionWords()
command! RobertDebugOn let g:robert_debug_loading=1 | let g:robert_debug_highlights=1
command! RobertDebugOff unlet! g:robert_debug_loading g:robert_debug_highlights

" ============================================================================
" Keybindings
" ============================================================================

nnoremap <leader>rs :ReaderToggleCached<CR>

" ============================================================================
" Configuration Examples
" ============================================================================
"
" Add to your .vimrc:
"
" " Change highlight style (options: underline, background, dim, bold)
" let g:robert_cache_highlight_style = 'underline'
"
" " Use a different cache file location
" let g:robert_cache_file = expand('~/my-custom-cache.csv')
"
" " Auto-enable for certain file types
" augroup MyRobertCache
"     autocmd!
"     autocmd FileType text,markdown ReaderShowCached
" augroup END
"
" " Custom keybinding
" nnoremap <F8> :ReaderToggleCached<CR>
"
" ============================================================================

