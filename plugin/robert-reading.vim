" Robert Reading Mode - Highlight word, sentence, and paragraph while reading
"
" Usage: :RobertReadingMode to toggle on/off
" Shows three levels of context:
"   - Word: Current word under cursor (brightest)
"   - Sentence: Current sentence (medium)
"   - Paragraph: Current paragraph (subtle)

" ============================================================================
" Configuration
" ============================================================================

let g:robert_reading_mode = 0

" ============================================================================
" Highlight Setup
" ============================================================================

function! s:SetupHighlights()
    " Paragraph: Subtle warm background (widest context)
    highlight RobertActiveParagraph guibg=#2A2520 ctermbg=234
    
    " Sentence: Medium highlight (middle context)
    highlight RobertActiveSentence guibg=#2A3520 ctermbg=235
    
    " Word: Brightest highlight (narrowest focus)
    highlight RobertActiveWord guibg=#3A4A3A ctermbg=237 guifg=#B8E6B8 ctermfg=150 gui=NONE cterm=NONE
endfunction

call s:SetupHighlights()

" ============================================================================
" Reading Mode Functions
" ============================================================================

function! RobertToggleReadingMode()
    if g:robert_reading_mode
        call s:DisableReadingMode()
        echo 'Reading Mode: OFF'
    else
        call s:EnableReadingMode()
        echo 'Reading Mode: ON - Word, sentence, and paragraph highlighted'
    endif
endfunction

function! s:EnableReadingMode()
    let g:robert_reading_mode = 1
    
    augroup RobertReadingMode
        autocmd!
        autocmd CursorMoved,CursorMovedI * call s:UpdateReadingHighlights()
        autocmd BufLeave * call s:ClearReadingHighlights()
    augroup END
    
    call s:UpdateReadingHighlights()
endfunction

function! s:DisableReadingMode()
    let g:robert_reading_mode = 0
    
    augroup RobertReadingMode
        autocmd!
    augroup END
    
    call s:ClearReadingHighlights()
endfunction

function! s:UpdateReadingHighlights()
    if !g:robert_reading_mode
        return
    endif
    
    call s:ClearReadingHighlights()
    call s:HighlightCurrentParagraph()
    call s:HighlightCurrentSentence()
    call s:HighlightCurrentWord()
endfunction

function! s:HighlightCurrentWord()
    let word = expand('<cword>')
    if word != ''
        let pattern = '\<' . escape(word, '\') . '\>'
        let w:robert_word_match = matchadd('RobertActiveWord', pattern, -1)
    endif
endfunction

function! s:HighlightCurrentParagraph()
    let current_line = line('.')
    
    " Find start of paragraph
    let start_line = current_line
    while start_line > 1
        if getline(start_line - 1) =~ '^\s*$'
            break
        endif
        let start_line -= 1
    endwhile
    
    " Find end of paragraph
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
        let match_id = matchaddpos('RobertActiveParagraph', [lnum], -3)
        call add(w:robert_para_matches, match_id)
    endfor
endfunction

function! s:HighlightCurrentSentence()
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
    
    " Join paragraph lines into one string
    let para_text = ''
    let line_offsets = [0]
    for lnum in range(para_start, para_end)
        let line_text = getline(lnum)
        let para_text .= line_text . ' '
        call add(line_offsets, len(para_text))
    endfor
    
    " Calculate cursor position in paragraph text
    let cursor_offset = line_offsets[current_line - para_start] + current_col - 1
    
    " Find sentence boundaries (. ! ? followed by space or end)
    let sentence_start = 0
    let sentence_end = len(para_text)
    
    " Find start of sentence (search backwards for . ! ?)
    for i in range(cursor_offset - 1, 0, -1)
        if para_text[i] =~ '[.!?]' && (i + 1 >= len(para_text) || para_text[i + 1] =~ '\s')
            let sentence_start = i + 1
            break
        endif
    endfor
    
    " Find end of sentence (search forwards for . ! ?)
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
    
    " Convert offsets back to line/col positions and highlight
    if exists('w:robert_sent_matches')
        for match_id in w:robert_sent_matches
            silent! call matchdelete(match_id)
        endfor
    endif
    
    let w:robert_sent_matches = []
    
    for lnum in range(para_start, para_end)
        let line_start = line_offsets[lnum - para_start]
        let line_end = line_offsets[lnum - para_start + 1]
        
        " Check if this line contains part of the sentence
        if line_end > sentence_start && line_start < sentence_end
            let col_start = max([1, sentence_start - line_start + 1])
            let col_end = min([len(getline(lnum)), sentence_end - line_start])
            let length = col_end - col_start + 1
            
            if length > 0
                let match_id = matchaddpos('RobertActiveSentence', [[lnum, col_start, length]], -2)
                call add(w:robert_sent_matches, match_id)
            endif
        endif
    endfor
endfunction

function! s:ClearReadingHighlights()
    if exists('w:robert_word_match')
        silent! call matchdelete(w:robert_word_match)
        unlet w:robert_word_match
    endif
    
    if exists('w:robert_sent_matches')
        for match_id in w:robert_sent_matches
            silent! call matchdelete(match_id)
        endfor
        unlet w:robert_sent_matches
    endif
    
    if exists('w:robert_para_matches')
        for match_id in w:robert_para_matches
            silent! call matchdelete(match_id)
        endfor
        unlet w:robert_para_matches
    endif
endfunction

" ============================================================================
" Commands
" ============================================================================

command! RobertReadingMode call RobertToggleReadingMode()

" Optional keybinding (uncomment to enable)
" nnoremap <leader>r :RobertReadingMode<CR>

