" Selection Grep Vim Plugin - Extract selection with context to file
"
" Usage: Press ,, on any word or visual selection to grep it to a file with context

" ============================================================================
" Highlighting Setup
" ============================================================================

" Define highlight group for looked-up words/phrases
" Link to CursorLine to match theme's hover color
highlight default link LookupHighlight CursorLine

" Store match IDs per buffer to keep highlights persistent
if !exists('g:lookup_highlights')
    let g:lookup_highlights = {}
endif

" Store the patterns for each buffer (so we can recreate highlights)
if !exists('g:lookup_patterns')
    let g:lookup_patterns = {}
endif

" Track whether highlights are currently visible
if !exists('g:lookup_highlights_visible')
    let g:lookup_highlights_visible = 1
endif

" Initialize highlights for current buffer
function! s:InitBufferHighlights()
    let bufnr = bufnr('%')
    if !has_key(g:lookup_highlights, bufnr)
        let g:lookup_highlights[bufnr] = []
    endif
    if !has_key(g:lookup_patterns, bufnr)
        let g:lookup_patterns[bufnr] = []
    endif
endfunction

" Add highlight for text
function! s:HighlightText(text)
    call s:InitBufferHighlights()
    let bufnr = bufnr('%')
    
    " Escape special regex characters for very nomagic mode
    " In \V mode, only backslash is special, so escape backslash and forward slash
    let escaped = escape(a:text, '\/&~')
    let pattern = '\V' . escaped
    
    " Store the pattern for this buffer
    call add(g:lookup_patterns[bufnr], a:text)
    
    " Add the match and store the ID (only if highlights are visible)
    if g:lookup_highlights_visible
        try
            let match_id = matchadd('LookupHighlight', pattern, 10)
            call add(g:lookup_highlights[bufnr], match_id)
            " Silently highlight without triggering press-enter prompt
        catch /^Vim\%((\a\+)\)\=:E/
            " Silently fail
        endtry
    endif
endfunction

" Clear all highlights for current buffer
function! s:ClearHighlights()
    let bufnr = bufnr('%')
    if has_key(g:lookup_highlights, bufnr)
        for match_id in g:lookup_highlights[bufnr]
            silent! call matchdelete(match_id)
        endfor
        let g:lookup_highlights[bufnr] = []
    endif
    if has_key(g:lookup_patterns, bufnr)
        let g:lookup_patterns[bufnr] = []
    endif
endfunction

" Hide all highlights (but keep them tracked)
function! s:HideHighlights()
    " Remove all match highlights
    for bufnr in keys(g:lookup_highlights)
        if has_key(g:lookup_highlights, bufnr)
            for match_id in g:lookup_highlights[bufnr]
                silent! call matchdelete(match_id)
            endfor
            let g:lookup_highlights[bufnr] = []
        endif
    endfor
    let g:lookup_highlights_visible = 0
endfunction

" Show all highlights
function! s:ShowHighlights()
    " Recreate highlights from stored patterns
    for bufnr in keys(g:lookup_patterns)
        if has_key(g:lookup_patterns, bufnr) && len(g:lookup_patterns[bufnr]) > 0
            " Switch to the buffer temporarily if needed
            let current_buf = bufnr('%')
            if current_buf == bufnr
                " We're in the right buffer, add highlights
                for text in g:lookup_patterns[bufnr]
                    let escaped = escape(text, '\/&~')
                    let pattern = '\V' . escaped
                    try
                        let match_id = matchadd('LookupHighlight', pattern, 10)
                        call add(g:lookup_highlights[bufnr], match_id)
                    catch
                        " Silently skip if pattern fails
                    endtry
                endfor
            endif
        endif
    endfor
    let g:lookup_highlights_visible = 1
endfunction

" Toggle highlights visibility
function! s:ToggleHighlights()
    if g:lookup_highlights_visible
        call s:HideHighlights()
    else
        call s:ShowHighlights()
    endif
endfunction

" ============================================================================
" Context Extraction Functions
" ============================================================================

" Get the sentence containing the cursor
function! s:GetCurrentSentence()
    let current_line = line('.')
    let current_col = col('.')
    
    " Get paragraph boundaries
    let para_start = current_line
    while para_start > 1 && getline(para_start - 1) !~ '^\s*$'
        let para_start -= 1
    endwhile
    
    let para_end = current_line
    let last_line = line('$')
    while para_end < last_line && getline(para_end + 1) !~ '^\s*$'
        let para_end += 1
    endwhile
    
    " Join paragraph into one string
    let para_text = ''
    let line_offsets = [0]
    for lnum in range(para_start, para_end)
        let para_text .= getline(lnum) . ' '
        call add(line_offsets, len(para_text))
    endfor
    
    " Calculate cursor position in paragraph text
    let cursor_offset = line_offsets[current_line - para_start] + current_col - 1
    
    " Find sentence boundaries
    let sentence_start = 0
    let sentence_end = len(para_text)
    
    " Find start (search backwards for . ! ?)
    for i in range(cursor_offset - 1, 0, -1)
        if para_text[i] =~ '[.!?]' && (i + 1 >= len(para_text) || para_text[i + 1] =~ '\s')
            let sentence_start = i + 1
            break
        endif
    endfor
    
    " Find end (search forwards for . ! ?)
    for i in range(cursor_offset, len(para_text) - 1)
        if para_text[i] =~ '[.!?]' && (i + 1 >= len(para_text) || para_text[i + 1] =~ '\s')
            let sentence_end = i + 1
            break
        endif
    endfor
    
    " Skip leading whitespace
    while sentence_start < len(para_text) && para_text[sentence_start] =~ '\s'
        let sentence_start += 1
    endwhile
    
    let sentence = para_text[sentence_start : sentence_end - 1]
    return substitute(sentence, '\s\+', ' ', 'g')
endfunction

" Get the current paragraph
function! s:GetCurrentParagraph()
    let current_line = line('.')
    
    " Find start of paragraph
    let start_line = current_line
    while start_line > 1 && getline(start_line - 1) !~ '^\s*$'
        let start_line -= 1
    endwhile
    
    " Find end of paragraph
    let end_line = current_line
    let last_line = line('$')
    while end_line < last_line && getline(end_line + 1) !~ '^\s*$'
        let end_line += 1
    endwhile
    
    " Join lines
    let lines = getline(start_line, end_line)
    let paragraph = join(lines, ' ')
    return substitute(paragraph, '\s\+', ' ', 'g')
endfunction

" ============================================================================
" Main Lookup Functions
" ============================================================================

function! s:LookupWord(...)
    let word = s:GetWord(a:000)
    if word == ''
        return
    endif
    
    " Get context
    let sentence = s:GetCurrentSentence()
    let paragraph = s:GetCurrentParagraph()
    
    " Create JSON structure
    let data = {
        \ 'selection': word,
        \ 'phrase': sentence,
        \ 'paragraph': paragraph,
        \ 'file': expand('%:p')
        \ }
    
    " Write JSON to FIFO (single line, backgrounded)
    let json_str = json_encode(data)
    call system('echo ' . shellescape(json_str) . ' >> /tmp/robert-dict.fifo &')
    
    " Highlight the looked-up word
    call s:HighlightText(word)
endfunction

function! s:GetWord(args)
    if len(a:args) > 0 && a:args[0] != ''
        return a:args[0]
    else
        return expand('<cword>')
    endif
endfunction

" Get visually selected text
function! s:GetVisualSelection()
    " Save the current register content
    let old_reg = @"
    
    " Yank the visual selection into the unnamed register
    normal! gvy
    
    " Get the yanked text
    let text = @"
    
    " Restore the old register content
    let @" = old_reg
    
    " Replace newlines with spaces for multi-line selections
    let text = substitute(text, '\n', ' ', 'g')
    
    return text
endfunction

function! s:LookupVisualSelection()
    let text = s:GetVisualSelection()
    if text == ''
        return
    endif
    
    " Get context
    let sentence = s:GetCurrentSentence()
    let paragraph = s:GetCurrentParagraph()
    
    " Create JSON structure
    let data = {
        \ 'selection': text,
        \ 'phrase': sentence,
        \ 'paragraph': paragraph
        \ }
    
    " Write JSON to FIFO (single line, backgrounded)
    let json_str = json_encode(data)
    call system('echo ' . shellescape(json_str) . ' >> /tmp/robert-dict.fifo &')
    
    " Highlight the looked-up phrase
    call s:HighlightText(text)
endfunction

" ============================================================================
" Commands and Keybindings
" ============================================================================

command! -nargs=? SelectionGrep call s:LookupWord(<q-args>)
command! -nargs=? SGrep call s:LookupWord(<q-args>)
command! -nargs=? Grep call s:LookupWord(<q-args>)
command! ClearLookupHighlights call s:ClearHighlights()
command! ToggleLookupHighlights call s:ToggleHighlights()
command! HideLookupHighlights call s:HideHighlights()
command! ShowLookupHighlights call s:ShowHighlights()

" Keybindings
nnoremap <silent> <leader>g :SelectionGrep<CR>
nnoremap <silent> ,, :SelectionGrep<CR>

" Visual mode keybinding - grep selected text
vnoremap <silent> ,, :<C-u>call <SID>LookupVisualSelection()<CR>

" Toggle highlights visibility
nnoremap <silent> <leader>th :ToggleLookupHighlights<CR>

" Clear highlights permanently
nnoremap <silent> <leader>ch :ClearLookupHighlights<CR>

" Optional keybindings (uncomment to enable)
" nnoremap K :SelectionGrep<CR>
" nnoremap <F2> :SelectionGrep<CR>
