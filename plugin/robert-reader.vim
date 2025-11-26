" ============================================================================
" Robert Reader - Beautiful Reading Mode for Foreign Language Books
" ============================================================================
"
" A visually elegant reading plugin with soft, eye-friendly colors that
" highlights current word, sentence, and paragraph for maximum reading comfort.
"
" Features:
"   - Multiple beautiful themes with cozy backgrounds
"   - Soft, eye-friendly colors for long reading sessions
"   - Three-level context highlighting (word → sentence → paragraph)
"   - Inverted focus mode (darkens active paragraph, brightens context)
"   - Reading comfort features (subtle margin, soft cursor)
"   - Smooth visual hierarchy and warm ambiance
"
" Usage:
"   :ReaderMode          - Toggle reading mode
"   :ReaderTheme <name>  - Change theme (sepia/ocean/forest/twilight/rose/nord/light)
"   :ReaderFocus         - Toggle focus mode
"   :ReaderCenter        - Toggle subtle left margin
"   :ReaderEnableAll     - Enable everything: Reader Mode + Center + Cached words
"
" Keybindings:
"   <leader>rr - Toggle reading mode
"   <leader>rt - Cycle through themes
"   <leader>rf - Toggle focus mode
"   <leader>rc - Toggle subtle margin
"   <leader>ra - Enable ALL features (recommended!)
"
" ============================================================================

" ============================================================================
" Configuration
" ============================================================================

" Default settings
let g:robert_reader_enabled = 0
let g:robert_reader_focus_mode = 0
let g:robert_reader_centered = 0
let g:robert_reader_theme = get(g:, 'robert_reader_theme', 'sepia')
let g:robert_reader_intensity = get(g:, 'robert_reader_intensity', 'medium')

" Available themes
let s:available_themes = ['sepia', 'ocean', 'forest', 'twilight', 'rose', 'nord', 'light']
let s:current_theme_index = index(s:available_themes, g:robert_reader_theme)

" ============================================================================
" Color Themes
" ============================================================================

function! s:SetupTheme(theme)
    let g:robert_reader_theme = a:theme
    
    if a:theme == 'sepia'
        " Warm sepia theme - like reading by candlelight
        let l:base_bg = '#1C1814'
        let l:para_bg = '#2A241E'
        let l:sent_bg = '#352E26'
        let l:word_bg = '#453C32'
        let l:word_fg = '#C8B597'
        let l:focus_fg = '#453C32'
        let l:normal_fg = '#9A8A7A'
        
    elseif a:theme == 'ocean'
        " Cool ocean blue - calm evening by the sea
        let l:base_bg = '#141A22'
        let l:para_bg = '#1C2430'
        let l:sent_bg = '#242E3C'
        let l:word_bg = '#2E3A4A'
        let l:word_fg = '#88A7B6'
        let l:focus_fg = '#2E3A4A'
        let l:normal_fg = '#7A95A8'
        
    elseif a:theme == 'forest'
        " Soft green forest - reading in a woodland glade
        let l:base_bg = '#151E15'
        let l:para_bg = '#1C261C'
        let l:sent_bg = '#243228'
        let l:word_bg = '#2E3E32'
        let l:word_fg = '#98B898'
        let l:focus_fg = '#2E3E32'
        let l:normal_fg = '#7A9A7A'
        
    elseif a:theme == 'twilight'
        " Purple twilight - cozy evening with lavender candles
        let l:base_bg = '#1A1520'
        let l:para_bg = '#251F2C'
        let l:sent_bg = '#2F2838'
        let l:word_bg = '#3A3444'
        let l:word_fg = '#B4A4C8'
        let l:focus_fg = '#3A3444'
        let l:normal_fg = '#9A8AAA'
        
    elseif a:theme == 'rose'
        " Soft rose - warm reading nook with rose-tinted ambiance
        let l:base_bg = '#1C161A'
        let l:para_bg = '#281E24'
        let l:sent_bg = '#332630'
        let l:word_bg = '#3E323A'
        let l:word_fg = '#C8A4B4'
        let l:focus_fg = '#3E323A'
        let l:normal_fg = '#AA8A9A'
        
    elseif a:theme == 'nord'
        " Nord-inspired - cozy nordic cabin in winter
        let l:base_bg = '#1E2228'
        let l:para_bg = '#262C36'
        let l:sent_bg = '#303844'
        let l:word_bg = '#3A4452'
        let l:word_fg = '#81A1C1'
        let l:focus_fg = '#3A4452'
        let l:normal_fg = '#7A90A8'
        
    elseif a:theme == 'light'
        " Light theme - soft paper with warm tint
        let l:base_bg = '#FBF8F0'
        let l:para_bg = '#F0EDE5'
        let l:sent_bg = '#E5E0D5'
        let l:word_bg = '#D8D3C5'
        let l:word_fg = '#5A5A4A'
        let l:focus_fg = '#D8D3C5'
        let l:normal_fg = '#7A7A6A'
        
    else
        " Default to sepia
        return s:SetupTheme('sepia')
    endif
    
    " Apply color scheme with softer colors and cozy backgrounds
    execute 'highlight Normal guibg=' . l:base_bg . ' guifg=' . l:normal_fg . ' ctermbg=233 ctermfg=246'
    execute 'highlight ReaderParagraph guibg=' . l:para_bg . ' ctermbg=234'
    execute 'highlight ReaderSentence guibg=' . l:sent_bg . ' ctermbg=235'
    execute 'highlight ReaderWord guibg=' . l:word_bg . ' guifg=' . l:word_fg . ' ctermbg=237 ctermfg=150 gui=bold cterm=bold'
    execute 'highlight ReaderFocusedText guifg=' . l:focus_fg . ' ctermfg=242'
    
    " Soft cursor - barely visible, not distracting
    execute 'highlight Cursor guibg=' . l:focus_fg . ' guifg=' . l:base_bg . ' ctermbg=242'
    execute 'highlight iCursor guibg=' . l:focus_fg . ' guifg=' . l:base_bg . ' ctermbg=242'
    execute 'highlight lCursor guibg=' . l:focus_fg . ' guifg=' . l:base_bg . ' ctermbg=242'
    
    " Very subtle cursorline - just a hint of presence
    execute 'highlight CursorLine guibg=' . l:para_bg . ' ctermbg=234 gui=NONE cterm=NONE'
    execute 'highlight CursorLineNr guifg=' . l:focus_fg . ' guibg=' . l:para_bg . ' ctermfg=242 ctermbg=234'
    
    " Margin columns - match base background perfectly
    execute 'highlight FoldColumn guibg=' . l:base_bg . ' guifg=' . l:base_bg . ' ctermbg=233 ctermfg=233'
    execute 'highlight SignColumn guibg=' . l:base_bg . ' ctermbg=233'
    execute 'highlight LineNr guibg=' . l:base_bg . ' guifg=' . l:focus_fg . ' ctermbg=233 ctermfg=242'
    
    " Additional cozy touches
    execute 'highlight NonText guibg=' . l:base_bg . ' guifg=' . l:focus_fg . ' ctermbg=233 ctermfg=242'
    execute 'highlight EndOfBuffer guibg=' . l:base_bg . ' guifg=' . l:focus_fg . ' ctermbg=233 ctermfg=242'
    
    " Subtle border for visual separation
    execute 'highlight ReaderBorder guifg=' . l:sent_bg . ' ctermfg=235'
endfunction

" ============================================================================
" Reading Mode Functions
" ============================================================================

function! RobertReaderToggle()
    if g:robert_reader_enabled
        call s:DisableReaderMode()
        echo '📖 Reader Mode: OFF'
    else
        call s:EnableReaderMode()
        echo '📖 Reader Mode: ON [' . g:robert_reader_theme . ' theme]'
    endif
endfunction

function! s:EnableReaderMode()
    let g:robert_reader_enabled = 1
    
    " Setup theme
    call s:SetupTheme(g:robert_reader_theme)
    
    " Configure comfortable reading settings
    setlocal cursorline
    setlocal wrap
    setlocal linebreak
    setlocal breakindent
    setlocal showbreak=↪\ 
    
    " Improve text rendering
    if has('gui_running') || has('termguicolors')
        setlocal termguicolors
    endif
    
    " Auto-update highlights on cursor movement
    augroup RobertReader
        autocmd!
        autocmd CursorMoved,CursorMovedI * call s:UpdateReadingHighlights()
        autocmd BufLeave * call s:ClearReadingHighlights()
        autocmd ColorScheme * call s:SetupTheme(g:robert_reader_theme)
    augroup END
    
    call s:UpdateReadingHighlights()
endfunction

function! s:DisableReaderMode()
    let g:robert_reader_enabled = 0
    
    augroup RobertReader
        autocmd!
    augroup END
    
    call s:ClearReadingHighlights()
    
    " Restore default settings
    setlocal nocursorline
    
    " Restore normal text color
    highlight clear Normal
    
    if g:robert_reader_focus_mode
        call s:DisableFocusMode()
    endif
    
    if g:robert_reader_centered
        call s:DisableCentering()
    endif
endfunction

" ============================================================================
" Highlighting Functions
" ============================================================================

function! s:UpdateReadingHighlights()
    if !g:robert_reader_enabled
        return
    endif
    
    call s:ClearReadingHighlights()
    call s:HighlightCurrentParagraph()
    call s:HighlightCurrentSentence()
    call s:HighlightCurrentWord()
    
    if g:robert_reader_focus_mode
        call s:ApplyFocusMode()
    endif
endfunction

function! s:HighlightCurrentWord()
    " Highlight the word under cursor with emphasis
    let word = expand('<cword>')
    if word != ''
        " Use word boundaries for precise matching
        let pattern = '\<' . escape(word, '\') . '\>'
        let w:reader_word_match = matchadd('ReaderWord', pattern, 10)
    endif
endfunction

function! s:HighlightCurrentSentence()
    let current_line = line('.')
    let current_col = col('.')
    
    " Get paragraph boundaries
    let para_start = s:FindParagraphStart(current_line)
    let para_end = s:FindParagraphEnd(current_line)
    
    " Build paragraph text with position tracking
    let [para_text, line_offsets] = s:BuildParagraphText(para_start, para_end)
    
    " Find sentence containing cursor
    let cursor_offset = line_offsets[current_line - para_start] + current_col - 1
    let [sent_start, sent_end] = s:FindSentenceBounds(para_text, cursor_offset)
    
    " Convert back to line positions and highlight
    call s:HighlightTextRange(para_start, para_end, line_offsets, sent_start, sent_end, 'ReaderSentence', 'reader_sent_matches', 5)
endfunction

function! s:HighlightCurrentParagraph()
    let current_line = line('.')
    let para_start = s:FindParagraphStart(current_line)
    let para_end = s:FindParagraphEnd(current_line)
    
    " Highlight entire paragraph with subtle background
    let w:reader_para_matches = []
    for lnum in range(para_start, para_end)
        let match_id = matchaddpos('ReaderParagraph', [lnum], 1)
        call add(w:reader_para_matches, match_id)
    endfor
endfunction

" ============================================================================
" Helper Functions
" ============================================================================

function! s:FindParagraphStart(line)
    let start = a:line
    while start > 1 && getline(start - 1) !~ '^\s*$'
        let start -= 1
    endwhile
    return start
endfunction

function! s:FindParagraphEnd(line)
    let end = a:line
    let last = line('$')
    while end < last && getline(end + 1) !~ '^\s*$'
        let end += 1
    endwhile
    return end
endfunction

function! s:BuildParagraphText(start, end)
    let text = ''
    let offsets = [0]
    for lnum in range(a:start, a:end)
        let line_text = getline(lnum)
        let text .= line_text . ' '
        call add(offsets, len(text))
    endfor
    return [text, offsets]
endfunction

function! s:FindSentenceBounds(text, cursor_pos)
    let sent_start = 0
    let sent_end = len(a:text)
    
    " Find start (search backwards for sentence terminators)
    for i in range(a:cursor_pos - 1, 0, -1)
        if a:text[i] =~ '[.!?;:]' && (i + 1 >= len(a:text) || a:text[i + 1] =~ '\s')
            let sent_start = i + 1
            break
        endif
    endfor
    
    " Find end (search forwards for sentence terminators)
    for i in range(a:cursor_pos, len(a:text) - 1)
        if a:text[i] =~ '[.!?]' && (i + 1 >= len(a:text) || a:text[i + 1] =~ '\s')
            let sent_end = i + 1
            break
        endif
    endfor
    
    " Skip leading whitespace
    while sent_start < len(a:text) && a:text[sent_start] =~ '\s'
        let sent_start += 1
    endwhile
    
    return [sent_start, sent_end]
endfunction

function! s:HighlightTextRange(para_start, para_end, line_offsets, text_start, text_end, highlight_group, match_var, priority)
    let w:[a:match_var] = []
    
    for lnum in range(a:para_start, a:para_end)
        let line_start = a:line_offsets[lnum - a:para_start]
        let line_end = a:line_offsets[lnum - a:para_start + 1]
        
        " Check if this line overlaps with our text range
        if line_end > a:text_start && line_start < a:text_end
            let col_start = max([1, a:text_start - line_start + 1])
            let col_end = min([len(getline(lnum)), a:text_end - line_start])
            let length = col_end - col_start + 1
            
            if length > 0
                let match_id = matchaddpos(a:highlight_group, [[lnum, col_start, length]], a:priority)
                call add(w:[a:match_var], match_id)
            endif
        endif
    endfor
endfunction

function! s:ClearReadingHighlights()
    " Clear word highlight
    if exists('w:reader_word_match')
        silent! call matchdelete(w:reader_word_match)
        unlet w:reader_word_match
    endif
    
    " Clear sentence highlights
    if exists('w:reader_sent_matches')
        for match_id in w:reader_sent_matches
            silent! call matchdelete(match_id)
        endfor
        unlet w:reader_sent_matches
    endif
    
    " Clear paragraph highlights
    if exists('w:reader_para_matches')
        for match_id in w:reader_para_matches
            silent! call matchdelete(match_id)
        endfor
        unlet w:reader_para_matches
    endif
    
    " Clear focus mode
    if exists('w:reader_focus_matches')
        for match_id in w:reader_focus_matches
            silent! call matchdelete(match_id)
        endfor
        unlet w:reader_focus_matches
    endif
endfunction

" ============================================================================
" Focus Mode - Darkens Current Paragraph (Inverted Focus)
" ============================================================================

function! RobertReaderToggleFocus()
    if !g:robert_reader_enabled
        echo '📖 Enable Reader Mode first'
        return
    endif
    
    if g:robert_reader_focus_mode
        call s:DisableFocusMode()
        echo '🎯 Focus Mode: OFF'
    else
        call s:EnableFocusMode()
        echo '🎯 Focus Mode: ON (reading in darkness with bright context)'
    endif
endfunction

function! s:EnableFocusMode()
    let g:robert_reader_focus_mode = 1
    call s:UpdateReadingHighlights()
endfunction

function! s:DisableFocusMode()
    let g:robert_reader_focus_mode = 0
    if exists('w:reader_focus_matches')
        for match_id in w:reader_focus_matches
            silent! call matchdelete(match_id)
        endfor
        unlet w:reader_focus_matches
    endif
endfunction

function! s:ApplyFocusMode()
    " Dim the active paragraph - reading in darkness with bright context around
    let current_line = line('.')
    let para_start = s:FindParagraphStart(current_line)
    let para_end = s:FindParagraphEnd(current_line)
    
    let w:reader_focus_matches = []
    
    " Dim the current paragraph (inverted focus)
    for lnum in range(para_start, para_end)
        let match_id = matchaddpos('ReaderFocusedText', [lnum], 0)
        call add(w:reader_focus_matches, match_id)
    endfor
endfunction

" ============================================================================
" Theme Cycling
" ============================================================================

function! RobertReaderCycleTheme()
    let s:current_theme_index = (s:current_theme_index + 1) % len(s:available_themes)
    let new_theme = s:available_themes[s:current_theme_index]
    
    call s:SetupTheme(new_theme)
    
    if g:robert_reader_enabled
        call s:UpdateReadingHighlights()
    endif
    
    echo '🎨 Theme: ' . new_theme
endfunction

function! RobertReaderSetTheme(theme)
    if index(s:available_themes, a:theme) == -1
        echo '❌ Unknown theme. Available: ' . join(s:available_themes, ', ')
        return
    endif
    
    let s:current_theme_index = index(s:available_themes, a:theme)
    call s:SetupTheme(a:theme)
    
    if g:robert_reader_enabled
        call s:UpdateReadingHighlights()
    endif
    
    echo '🎨 Theme: ' . a:theme
endfunction

" ============================================================================
" Text Margin - Subtle Left Indentation
" ============================================================================

function! RobertReaderToggleCenter()
    if !g:robert_reader_enabled
        echo '📖 Enable Reader Mode first'
        return
    endif
    
    if g:robert_reader_centered
        call s:DisableCentering()
        echo '📐 Margin: OFF'
    else
        call s:EnableCentering()
        echo '📐 Margin: ON (subtle left indent)'
    endif
endfunction

function! s:EnableCentering()
    let g:robert_reader_centered = 1
    
    " Add subtle left margin (1-2 characters)
    setlocal foldcolumn=1
    setlocal number
    setlocal numberwidth=1
endfunction

function! s:DisableCentering()
    let g:robert_reader_centered = 0
    setlocal foldcolumn=0
    setlocal nonumber
endfunction

" ============================================================================
" All-in-One Command
" ============================================================================

function! RobertReaderEnableAll()
    " Enable Reader Mode
    if !g:robert_reader_enabled
        call s:EnableReaderMode()
    endif
    
    " Enable Center
    if !g:robert_reader_centered
        call s:EnableCentering()
    endif
    
    " Enable Cached word highlighting (if plugin is available)
    if exists(':ReaderShowCached')
        execute 'ReaderShowCached'
    endif
    
    echo '📖 Full Reading Mode: ON [' . g:robert_reader_theme . ' + center + cached words]'
endfunction

" ============================================================================
" Commands
" ============================================================================

command! ReaderMode call RobertReaderToggle()
command! ReaderFocus call RobertReaderToggleFocus()
command! ReaderCenter call RobertReaderToggleCenter()
command! ReaderThemeCycle call RobertReaderCycleTheme()
command! -nargs=1 -complete=customlist,s:CompleteThemes ReaderTheme call RobertReaderSetTheme(<q-args>)
command! ReaderEnableAll call RobertReaderEnableAll()

function! s:CompleteThemes(ArgLead, CmdLine, CursorPos)
    return filter(copy(s:available_themes), 'v:val =~ "^" . a:ArgLead')
endfunction

" ============================================================================
" Keybindings
" ============================================================================

nnoremap <leader>rr :ReaderMode<CR>
nnoremap <leader>rt :ReaderThemeCycle<CR>
nnoremap <leader>rf :ReaderFocus<CR>
nnoremap <leader>rc :ReaderCenter<CR>
nnoremap <leader>ra :ReaderEnableAll<CR>

" ============================================================================
" Initialize
" ============================================================================

call s:SetupTheme(g:robert_reader_theme)

" Optional: Auto-enable for certain file types
" augroup RobertReaderAuto
"     autocmd!
"     autocmd FileType text,markdown,txt :ReaderMode
" augroup END

" ============================================================================
" Configuration Examples
" ============================================================================
"
" Add to your .vimrc:
"
" " Set default theme
" let g:robert_reader_theme = 'ocean'
"
" " Auto-enable for text files
" augroup MyReaderMode
"     autocmd!
"     autocmd FileType text,markdown ReaderMode
" augroup END
"
" " Custom keybindings
" nnoremap <F9> :ReaderMode<CR>
" nnoremap <F10> :ReaderThemeCycle<CR>
"
" ============================================================================

