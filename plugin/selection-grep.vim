" Selection Grep Vim Plugin - Extract selection with context to file
"
" Usage: Press ,, on any word or visual selection to grep it to a file with context

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
        \ 'paragraph': paragraph
        \ }
    
    " Write to file and execute lookup
    let tmp_dir = exists('$TMP_VIM') ? $TMP_VIM : expand('<sfile>:p:h:h') . '/tmp'
    let word_file = tmp_dir . '/selection.json'
    " Format JSON with 4-space indentation and preserve French accents
    let json_str = json_encode(data)
    let formatted = system('python3 -c "import sys, json; print(json.dumps(json.loads(sys.stdin.read()), indent=4, ensure_ascii=False))"', json_str)
    call writefile(split(formatted, '\n'), word_file)
    
    let script_path = expand('<sfile>:p:h:h') . '/scripts/dict_watcher.py'
    silent! call system(script_path)
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
    let [line_start, column_start] = getpos("'<")[1:2]
    let [line_end, column_end] = getpos("'>")[1:2]
    let lines = getline(line_start, line_end)
    
    if len(lines) == 0
        return ''
    endif
    
    " Handle single line selection
    if len(lines) == 1
        return lines[0][column_start - 1 : column_end - 1]
    endif
    
    " Handle multi-line selection
    let lines[-1] = lines[-1][: column_end - 1]
    let lines[0] = lines[0][column_start - 1:]
    return join(lines, ' ')
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
    
    " Write to file and execute lookup
    let tmp_dir = exists('$TMP_VIM') ? $TMP_VIM : expand('<sfile>:p:h:h') . '/tmp'
    let word_file = tmp_dir . '/selection.json'
    " Format JSON with 4-space indentation and preserve French accents
    let json_str = json_encode(data)
    let formatted = system('python3 -c "import sys, json; print(json.dumps(json.loads(sys.stdin.read()), indent=4, ensure_ascii=False))"', json_str)
    call writefile(split(formatted, '\n'), word_file)
    
    let script_path = expand('<sfile>:p:h:h') . '/scripts/dict_watcher.py'
    silent! call system(script_path)
endfunction

" ============================================================================
" Commands and Keybindings
" ============================================================================

command! -nargs=? SelectionGrep call s:LookupWord(<q-args>)
command! -nargs=? SGrep call s:LookupWord(<q-args>)
command! -nargs=? Grep call s:LookupWord(<q-args>)

" Keybindings
nnoremap <leader>g :SelectionGrep<CR>
nnoremap ,, :SelectionGrep<CR>

" Visual mode keybinding - grep selected text
vnoremap ,, :<C-u>call <SID>LookupVisualSelection()<CR>

" Optional keybindings (uncomment to enable)
" nnoremap K :SelectionGrep<CR>
" nnoremap <F2> :SelectionGrep<CR>
