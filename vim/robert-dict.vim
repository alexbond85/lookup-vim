" Robert Dictionary Vim Plugin
" 
" DICTIONARY LOOKUP:
"   :RobertDict           - Look up word under cursor
"   :RobertDict maison    - Look up specific word
"   <leader>d             - Quick lookup word under cursor
"
" Popup navigation:
"   j/k or ↓/↑            - Scroll line by line
"   Ctrl-d/Ctrl-u         - Page down/up
"   q or Esc              - Close popup
"
" READING MODE (highlight active paragraph and word):
"   :RobertReadingMode    - Toggle reading mode ON/OFF
"   <leader>r             - Quick toggle (uncomment in code to enable)
"
" When reading mode is ON:
"   - Current paragraph gets subtle background highlight
"   - Word under cursor is highlighted across the whole file
"   - Updates automatically as you move cursor
"   - Only active when you explicitly enable it

" Define elegant highlight groups (Apple-inspired)
function! s:SetupHighlights()
    " Main word header - bold and prominent
    highlight RobertWord ctermfg=39 guifg=#007AFF gui=bold cterm=bold
    
    " Category tags - subtle accent
    highlight RobertCategory ctermfg=141 guifg=#AF87FF gui=italic cterm=italic
    
    " Definition text - clear and readable
    highlight RobertDefinition ctermfg=252 guifg=#D0D0D0 gui=NONE cterm=NONE
    
    " Examples - slightly dimmed with arrow
    highlight RobertExample ctermfg=246 guifg=#949494 gui=italic cterm=italic
    
    " Section headers - clean gray
    highlight RobertSection ctermfg=250 guifg=#BCBCBC gui=bold cterm=bold
    
    " Separator lines - minimal
    highlight RobertSeparator ctermfg=240 guifg=#585858 gui=NONE cterm=NONE
    
    " Popup background - clean and modern
    highlight RobertPopup ctermbg=235 guibg=#262626 ctermfg=252 guifg=#D0D0D0
endfunction

call s:SetupHighlights()

" ============================================================================
" Reading Mode - Highlight active paragraph and word
" ============================================================================

let g:robert_reading_mode = 0

" Toggle reading mode on/off
function! RobertToggleReadingMode()
    if g:robert_reading_mode
        call s:DisableReadingMode()
        echo 'Reading Mode: OFF'
    else
        call s:EnableReadingMode()
        echo 'Reading Mode: ON - Active paragraph and word highlighted'
    endif
endfunction

" Enable reading mode
function! s:EnableReadingMode()
    let g:robert_reading_mode = 1
    
    " Define reading mode highlights
    highlight RobertActiveParagraph guibg=#1C1C1C ctermbg=234
    highlight RobertActiveWord guibg=#3A3A3A ctermbg=237 gui=bold cterm=bold
    
    " Set up autocommands for dynamic highlighting
    augroup RobertReadingMode
        autocmd!
        autocmd CursorMoved,CursorMovedI * call s:UpdateReadingHighlights()
        autocmd BufLeave * call s:ClearReadingHighlights()
    augroup END
    
    " Initial highlight
    call s:UpdateReadingHighlights()
endfunction

" Disable reading mode
function! s:DisableReadingMode()
    let g:robert_reading_mode = 0
    
    " Remove autocommands
    augroup RobertReadingMode
        autocmd!
    augroup END
    
    " Clear highlights
    call s:ClearReadingHighlights()
endfunction

" Update highlights for current position
function! s:UpdateReadingHighlights()
    if !g:robert_reading_mode
        return
    endif
    
    call s:ClearReadingHighlights()
    
    " Highlight current word
    call s:HighlightCurrentWord()
    
    " Highlight current paragraph
    call s:HighlightCurrentParagraph()
endfunction

" Highlight the word under cursor
function! s:HighlightCurrentWord()
    let word = expand('<cword>')
    if word != ''
        " Match whole word only
        let pattern = '\<' . escape(word, '\') . '\>'
        let w:robert_word_match = matchadd('RobertActiveWord', pattern, -1)
    endif
endfunction

" Highlight the current paragraph
function! s:HighlightCurrentParagraph()
    " Find paragraph boundaries
    let current_line = line('.')
    
    " Find start of paragraph (blank line or start of file)
    let start_line = current_line
    while start_line > 1
        if getline(start_line - 1) =~ '^\s*$'
            break
        endif
        let start_line -= 1
    endwhile
    
    " Find end of paragraph (blank line or end of file)
    let end_line = current_line
    let last_line = line('$')
    while end_line < last_line
        if getline(end_line + 1) =~ '^\s*$'
            break
        endif
        let end_line += 1
    endwhile
    
    " Highlight the paragraph
    if exists('w:robert_para_matches')
        for match_id in w:robert_para_matches
            silent! call matchdelete(match_id)
        endfor
    endif
    
    let w:robert_para_matches = []
    for lnum in range(start_line, end_line)
        let match_id = matchaddpos('RobertActiveParagraph', [lnum], -2)
        call add(w:robert_para_matches, match_id)
    endfor
endfunction

" Clear all reading highlights
function! s:ClearReadingHighlights()
    " Clear word highlight
    if exists('w:robert_word_match')
        silent! call matchdelete(w:robert_word_match)
        unlet w:robert_word_match
    endif
    
    " Clear paragraph highlights
    if exists('w:robert_para_matches')
        for match_id in w:robert_para_matches
            silent! call matchdelete(match_id)
        endfor
        unlet w:robert_para_matches
    endif
endfunction

" ============================================================================
" Dictionary Lookup Functions
" ============================================================================

function! s:ShowDefinition(...)
    " Get the word: either from argument or under cursor
    if a:0 > 0 && a:1 != ''
        let word = a:1
    else
        let word = expand('<cword>')
    endif
    
    if word == ''
        echo 'Error: No word to look up'
        return
    endif
    
    " Call robert-dict with JSON format
    let result = system('robert-dict ' . shellescape(word) . ' --format json')
    
    " Check if command failed
    if v:shell_error
        echo 'Error: Could not fetch definition for "' . word . '"'
        return
    endif
    
    " Parse JSON
    try
        let json = json_decode(result)
    catch
        echo 'Error: Could not parse JSON response'
        return
    endtry
    
    " Handle conjugation result
    if has_key(json, 'type') && json.type == 'conjugation'
        let lines = ['Conjugation: ' . json.original_word . ' → ' . json.redirected_to, '']
        call add(lines, json.message)
        if has_key(json, 'definition_url') && json.definition_url != v:null
            call add(lines, '')
            call add(lines, 'Definition: ' . json.definition_url)
        endif
        " Show the popup with conjugation info
        call s:ShowPopup(lines)
        return
    endif
    
    " Format word result output
    let lines = ['Word: ' . json.word, '']
    
    " Add definitions with categories
    if has_key(json, 'definitions') && len(json.definitions) > 0
        let current_category = ''
        for def in json.definitions
            " Show category if it changes
            if has_key(def, 'category') && def.category != current_category
                if current_category != ''
                    call add(lines, '')
                endif
                call add(lines, '[' . def.category . ']')
                let current_category = def.category
            endif
            
            " Add the definition
            if has_key(def, 'definition')
                call add(lines, '  • ' . def.definition)
            endif
            
            " Add examples (limit to 2 per definition)
            if has_key(def, 'examples') && len(def.examples) > 0
                let max_ex = min([len(def.examples), 2])
                for i in range(max_ex)
                    call add(lines, '    → ' . def.examples[i])
                endfor
            endif
        endfor
        call add(lines, '')
    endif
    
    " Add usage examples (limit to first 3 for readability)
    if has_key(json, 'usage_examples') && len(json.usage_examples) > 0
        call add(lines, 'Usage Examples:')
        let max_examples = min([len(json.usage_examples), 3])
        for i in range(max_examples)
            let example = json.usage_examples[i]
            call add(lines, '  ' . example)
        endfor
        call add(lines, '')
    endif
    
    " Show the popup
    call s:ShowPopup(lines)
endfunction

function! s:ShowPopup(lines)
    " Show in popup/floating window
    if has('nvim')
        " Neovim floating window positioned near cursor
        let buf = nvim_create_buf(v:false, v:true)
        call nvim_buf_set_lines(buf, 0, -1, v:true, a:lines)
        
        " Calculate window size
        let width = 80
        let height = min([len(a:lines), 20])
        
        let opts = {
            \ 'relative': 'cursor',
            \ 'width': width,
            \ 'height': height,
            \ 'row': 1,
            \ 'col': 0,
            \ 'style': 'minimal',
            \ 'border': 'rounded'
            \ }
        
        " Open window and enter it for scrolling
        let win = nvim_open_win(buf, v:true, opts)
        
        " Set window options
        call nvim_win_set_option(win, 'wrap', v:true)
        call nvim_win_set_option(win, 'winhl', 'Normal:RobertPopup')
        
        " Set buffer options
        setlocal buftype=nofile
        setlocal bufhidden=wipe
        setlocal nomodifiable
        setlocal noswapfile
        setlocal filetype=robert
        
        " Apply syntax highlighting
        call s:ApplySyntaxHighlighting()
        
        " Set up key mappings to close the popup
        nnoremap <buffer><silent> q :close<CR>
        nnoremap <buffer><silent> <Esc> :close<CR>
        
        " Info message
        echo 'Scroll: j/k/Ctrl-d/Ctrl-u | Close: q or Esc'
    else
        " Vim 8.2+ popup positioned near cursor (above)
        let s:popup_id = popup_create(a:lines, {
            \ 'line': 'cursor-1',
            \ 'col': 'cursor',
            \ 'pos': 'botleft',
            \ 'moved': 'any',
            \ 'padding': [0, 1, 0, 1],
            \ 'border': [],
            \ 'borderchars': ['─', '│', '─', '│', '┌', '┐', '┘', '└'],
            \ 'minwidth': 80,
            \ 'maxwidth': 80,
            \ 'minheight': 10,
            \ 'maxheight': 20,
            \ 'scrollbar': 1,
            \ 'wrap': 1,
            \ 'resize': 0,
            \ 'filter': 's:PopupFilter',
            \ 'highlight': 'RobertPopup'
            \ })
        
        " Apply text properties for syntax highlighting
        call s:ApplyVimHighlighting(s:popup_id, a:lines)
        
        echo 'Scroll: j/k | Page: Ctrl-d/Ctrl-u | Close: q or Esc'
    endif
endfunction

" Apply syntax highlighting for Neovim
function! s:ApplySyntaxHighlighting()
    syntax clear
    
    " Header separators (═══)
    syntax match RobertSeparator /^═\+$/
    
    " Word header (centered, uppercase)
    syntax match RobertWord /^\s*[A-ZÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜŸ][A-ZÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜŸ ]*$/
    
    " Category tags [nom féminin], [verbe], etc
    syntax match RobertCategory /\[.\{-}\]/
    
    " Section headers (EXEMPLES, MOTS FRÉQUEMMENT)
    syntax match RobertSection /^[A-ZÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜŸ' ]\+$/
    syntax match RobertSeparator /^─\+$/
    
    " Examples with arrows
    syntax match RobertExample /^\s*→.*$/
    syntax match RobertExample /^\s*•.*$/
    
    " Numbered definitions
    syntax match RobertDefinition /^\d\+\..*/
endfunction

" Apply highlighting for Vim using text properties
function! s:ApplyVimHighlighting(winid, lines)
    let bufnr = winbufnr(a:winid)
    
    " Define text property types if not already defined
    if empty(prop_type_get('robert_word', {'bufnr': bufnr}))
        call prop_type_add('robert_word', {'highlight': 'RobertWord', 'bufnr': bufnr})
        call prop_type_add('robert_category', {'highlight': 'RobertCategory', 'bufnr': bufnr})
        call prop_type_add('robert_section', {'highlight': 'RobertSection', 'bufnr': bufnr})
        call prop_type_add('robert_example', {'highlight': 'RobertExample', 'bufnr': bufnr})
        call prop_type_add('robert_separator', {'highlight': 'RobertSeparator', 'bufnr': bufnr})
        call prop_type_add('robert_definition', {'highlight': 'RobertDefinition', 'bufnr': bufnr})
    endif
    
    " Apply properties to lines
    for idx in range(len(a:lines))
        let line = a:lines[idx]
        let lnum = idx + 1
        
        " Separators
        if line =~ '^[═─]\+$'
            call prop_add(lnum, 1, {'length': len(line), 'type': 'robert_separator', 'bufnr': bufnr})
        " Word header (uppercase, centered)
        elseif line =~ '^\s*[A-ZÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜŸ][A-ZÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜŸ ]*$' && line !~ '^[A-Z ]\{20,\}$'
            call prop_add(lnum, 1, {'length': len(line), 'type': 'robert_word', 'bufnr': bufnr})
        " Section headers
        elseif line =~ '^[A-ZÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜŸ'' ]\+$'
            call prop_add(lnum, 1, {'length': len(line), 'type': 'robert_section', 'bufnr': bufnr})
        " Categories
        elseif line =~ '\['
            let start = match(line, '\[')
            let end = match(line, '\]')
            if start >= 0 && end > start
                call prop_add(lnum, start + 1, {'length': end - start + 1, 'type': 'robert_category', 'bufnr': bufnr})
            endif
        " Examples
        elseif line =~ '^\s*[→•]'
            call prop_add(lnum, 1, {'length': len(line), 'type': 'robert_example', 'bufnr': bufnr})
        " Numbered definitions
        elseif line =~ '^\d\+\.'
            call prop_add(lnum, 1, {'length': len(line), 'type': 'robert_definition', 'bufnr': bufnr})
        endif
    endfor
endfunction

" Filter function for Vim popup scrolling
function! s:PopupFilter(winid, key) abort
    " Get current position and content info
    let pos = popup_getpos(a:winid)
    let firstline = pos.firstline
    let lastline = pos.lastline
    
    " Get buffer to check total lines
    let bufnr = winbufnr(a:winid)
    let total_lines = line('$', a:winid)
    
    " Scroll down one line
    if a:key == 'j' || a:key == "\<Down>"
        " Only scroll if not at bottom
        if lastline < total_lines
            call popup_setoptions(a:winid, {'firstline': firstline + 1})
        endif
        return 1
    " Scroll up one line
    elseif a:key == 'k' || a:key == "\<Up>"
        " Only scroll if not at top
        if firstline > 1
            call popup_setoptions(a:winid, {'firstline': firstline - 1})
        endif
        return 1
    " Page down
    elseif a:key == "\<C-D>" || a:key == "\<PageDown>"
        let pagesize = lastline - firstline
        let new_firstline = firstline + pagesize
        " Don't scroll past the end
        if lastline < total_lines
            call popup_setoptions(a:winid, {'firstline': new_firstline})
        endif
        return 1
    " Page up
    elseif a:key == "\<C-U>" || a:key == "\<PageUp>"
        let pagesize = lastline - firstline
        let new_firstline = firstline - pagesize
        " Don't scroll past the beginning
        if new_firstline < 1
            call popup_setoptions(a:winid, {'firstline': 1})
        else
            call popup_setoptions(a:winid, {'firstline': new_firstline})
        endif
        return 1
    " Close popup
    elseif a:key == 'q' || a:key == 'x' || a:key == "\<Esc>"
        call popup_close(a:winid)
        return 1
    endif
    
    return 0
endfunction

" ============================================================================
" Commands and Keybindings
" ============================================================================

" Dictionary lookup command
command! -nargs=? RobertDict call s:ShowDefinition(<q-args>)

" Reading mode toggle command
command! RobertReadingMode call RobertToggleReadingMode()

" Key mappings
" <leader>d - Look up word under cursor
nnoremap <leader>d :RobertDict<CR>

" <leader>r - Toggle reading mode (optional, uncomment to use)
" nnoremap <leader>r :RobertReadingMode<CR>