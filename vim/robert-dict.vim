" Robert Dictionary Vim Plugin
" 
" ============================================================================
" DICTIONARY LOOKUP - Multiple ways (choose your favorite):
" ============================================================================
"   COMMANDS:
"     :R                    - Super short! Just :R and press Enter
"     :Dict                 - Short and clear
"     :RobertDict           - Full name
"   
"   KEYBOARD SHORTCUTS:
"     ,,                    - Double comma (FASTEST! Already enabled)
"     \d                    - Leader+d (default leader is \)
"     K                     - Capital K (uncomment to enable)
"     <F2>                  - Function key (uncomment to enable)
"
" Popup navigation:
"   j/k or ↓/↑            - Scroll line by line
"   Ctrl-d/Ctrl-u         - Page down/up
"   ANY OTHER KEY         - Closes the popup instantly!
"
" ============================================================================
" READING MODE (highlight active paragraph and word):
" ============================================================================
"   :RobertReadingMode    - Toggle reading mode ON/OFF
"   <leader>r             - Quick toggle (uncomment to enable)
"
" When reading mode is ON:
"   - Current paragraph gets subtle background highlight
"   - Word under cursor is highlighted across the whole file
"   - Updates automatically as you move cursor
"   - Only active when you explicitly enable it
"
" ============================================================================
" Configuration Variables (customize these in your .vimrc)
" ============================================================================

" Maximum number of examples to show per definition (default: 2)
if !exists('g:robert_max_examples_per_def')
    let g:robert_max_examples_per_def = 2
endif

" Maximum number of usage examples to show (default: 3)
if !exists('g:robert_max_usage_examples')
    let g:robert_max_usage_examples = 3
endif

" Popup window width (default: 80)
if !exists('g:robert_popup_width')
    let g:robert_popup_width = 80
endif

" Popup window max height (default: 20)
if !exists('g:robert_popup_max_height')
    let g:robert_popup_max_height = 20
endif

" Popup window min height (default: 10)
if !exists('g:robert_popup_min_height')
    let g:robert_popup_min_height = 10
endif

" ============================================================================
" Highlight Groups Setup
" ============================================================================

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

" ============================================================================
" Main Dictionary Lookup Function
" ============================================================================
"
" This is the entry point for dictionary lookups. It:
" 1. Determines the word to look up (from argument or cursor)
" 2. Calls the CLI tool to fetch data
" 3. Parses the JSON response
" 4. Formats and displays the result in a popup

function! s:ShowDefinition(...)
    let word = s:GetWordToLookup(a:000)
    if word == ''
        echo 'Error: No word to look up'
        return
    endif
    
    " Fetch definition data from CLI tool
    let json = s:FetchDefinitionData(word)
    if empty(json)
        return
    endif
    
    " Format the result based on type
    let lines = s:FormatDefinitionResult(json)
    
    " Display in popup window
    call s:ShowPopup(lines)
endfunction

" ============================================================================
" Helper Functions for Dictionary Lookup
" ============================================================================

" Get the word to look up: either from argument or under cursor
function! s:GetWordToLookup(args)
    if len(a:args) > 0 && a:args[0] != ''
        return a:args[0]
    else
        return expand('<cword>')
    endif
endfunction

" Fetch definition data from robert-dict CLI tool
" Returns: Dictionary containing parsed JSON response, or empty dict on error
function! s:FetchDefinitionData(word)
    " Call robert-dict with JSON format
    let result = system('robert-dict ' . shellescape(a:word) . ' --format json')
    
    " Check if command failed
    if v:shell_error
        echo 'Error: Could not fetch definition for "' . a:word . '"'
        return {}
    endif
    
    " Parse JSON
    try
        return json_decode(result)
    catch
        echo 'Error: Could not parse JSON response'
        return {}
    endtry
endfunction

" Format the definition result into display lines
" Handles both word definitions and conjugation results
function! s:FormatDefinitionResult(json)
    " Handle conjugation result
    if has_key(a:json, 'type') && a:json.type == 'conjugation'
        return s:FormatConjugationResult(a:json)
    endif
    
    " Handle word result
    return s:FormatWordResult(a:json)
endfunction

" Format a conjugation result
function! s:FormatConjugationResult(json)
    let lines = ['Conjugation: ' . a:json.original_word . ' → ' . a:json.redirected_to, '']
    call add(lines, a:json.message)
    
    if has_key(a:json, 'definition_url') && a:json.definition_url != v:null
        call add(lines, '')
        call add(lines, 'Definition: ' . a:json.definition_url)
    endif
    
    return lines
endfunction

" Format a word result with definitions and examples
function! s:FormatWordResult(json)
    let lines = ['Word: ' . a:json.word, '']
    
    " Add definitions
    if has_key(a:json, 'definitions') && len(a:json.definitions) > 0
        call extend(lines, s:FormatDefinitions(a:json.definitions))
    endif
    
    " Add usage examples
    if has_key(a:json, 'usage_examples') && len(a:json.usage_examples) > 0
        call extend(lines, s:FormatUsageExamples(a:json.usage_examples))
    endif
    
    return lines
endfunction

" Format definitions with categories and examples
function! s:FormatDefinitions(definitions)
    let lines = []
    let current_category = ''
    
    for def in a:definitions
        " Show category header if it changes
        if has_key(def, 'category') && def.category != current_category
            if current_category != ''
                call add(lines, '')
            endif
            call add(lines, '[' . def.category . ']')
            let current_category = def.category
        endif
        
        " Add the definition text
        if has_key(def, 'definition')
            call add(lines, '  • ' . def.definition)
        endif
        
        " Add example sentences (limited by config)
        if has_key(def, 'examples') && len(def.examples) > 0
            let max_ex = min([len(def.examples), g:robert_max_examples_per_def])
            for i in range(max_ex)
                call add(lines, '    → ' . def.examples[i])
            endfor
        endif
    endfor
    
    call add(lines, '')
    return lines
endfunction

" Format usage examples section
function! s:FormatUsageExamples(examples)
    let lines = ['Usage Examples:']
    let max_examples = min([len(a:examples), g:robert_max_usage_examples])
    
    for i in range(max_examples)
        call add(lines, '  ' . a:examples[i])
    endfor
    
    call add(lines, '')
    return lines
endfunction

" ============================================================================
" Popup Window Display
" ============================================================================
"
" Shows the formatted definition in a popup/floating window
" Handles both Neovim (floating window) and Vim 8.2+ (popup window)

function! s:ShowPopup(lines)
    if has('nvim')
        call s:ShowNeovimFloatingWindow(a:lines)
    else
        call s:ShowVimPopup(a:lines)
    endif
endfunction

" Create and configure Neovim floating window
function! s:ShowNeovimFloatingWindow(lines)
    " Create buffer and populate with content
    let buf = nvim_create_buf(v:false, v:true)
    call nvim_buf_set_lines(buf, 0, -1, v:true, a:lines)
    
    " Calculate window dimensions (using config variables)
    let width = g:robert_popup_width
    let height = min([len(a:lines), g:robert_popup_max_height])
    
    " Window positioning options
    let opts = {
        \ 'relative': 'cursor',
        \ 'width': width,
        \ 'height': height,
        \ 'row': 1,
        \ 'col': 0,
        \ 'style': 'minimal',
        \ 'border': 'rounded'
        \ }
    
    " Open window (enter it for scrolling support)
    let win = nvim_open_win(buf, v:true, opts)
    
    " Configure window appearance
    call nvim_win_set_option(win, 'wrap', v:true)
    call nvim_win_set_option(win, 'winhl', 'Normal:RobertPopup')
    
    " Configure buffer settings
    setlocal buftype=nofile
    setlocal bufhidden=wipe
    setlocal nomodifiable
    setlocal noswapfile
    setlocal filetype=robert
    
    " Apply syntax highlighting
    call s:ApplySyntaxHighlighting()
    
    " Set up navigation key mappings
    call s:SetupNeovimPopupMappings()
    
    " Clear message when window closes
    autocmd WinClosed <buffer> echo ''
    
    " Show usage message
    echo 'Scroll: j/k/Ctrl-d/Ctrl-u | Any other key closes'
endfunction

" Set up key mappings for Neovim popup navigation
function! s:SetupNeovimPopupMappings()
    " Scrolling keys - keep popup open
    nnoremap <buffer><silent> j j
    nnoremap <buffer><silent> k k
    nnoremap <buffer><silent> <Down> <Down>
    nnoremap <buffer><silent> <Up> <Up>
    nnoremap <buffer><silent> <C-d> <C-d>
    nnoremap <buffer><silent> <C-u> <C-u>
    
    " Map all printable keys to close the popup
    for key in split('abcdefghilmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:''",.<>?/~` ', '\zs')
        execute 'nnoremap <buffer><silent> ' . key . ' :close<CR>:echo ''''<CR>'
    endfor
    
    " Special keys that close popup
    nnoremap <buffer><silent> <Esc> :close<CR>:echo ''<CR>
    nnoremap <buffer><silent> <CR> :close<CR>:echo ''<CR>
    nnoremap <buffer><silent> <Space> :close<CR>:echo ''<CR>
    nnoremap <buffer><silent> <BS> :close<CR>:echo ''<CR>
    nnoremap <buffer><silent> <Tab> :close<CR>:echo ''<CR>
endfunction

" Create and configure Vim 8.2+ popup window
function! s:ShowVimPopup(lines)
    let s:popup_id = popup_create(a:lines, {
        \ 'line': 'cursor-1',
        \ 'col': 'cursor',
        \ 'pos': 'botleft',
        \ 'moved': 'any',
        \ 'padding': [0, 1, 0, 1],
        \ 'border': [],
        \ 'borderchars': ['─', '│', '─', '│', '┌', '┐', '┘', '└'],
        \ 'minwidth': g:robert_popup_width,
        \ 'maxwidth': g:robert_popup_width,
        \ 'minheight': g:robert_popup_min_height,
        \ 'maxheight': g:robert_popup_max_height,
        \ 'scrollbar': 1,
        \ 'wrap': 1,
        \ 'resize': 0,
        \ 'filter': 's:PopupFilter',
        \ 'callback': 's:PopupCallback',
        \ 'highlight': 'RobertPopup'
        \ })
    
    " Apply text properties for syntax highlighting
    call s:ApplyVimHighlighting(s:popup_id, a:lines)
    
    " Show usage message
    echo 'Scroll: j/k/Ctrl-d/Ctrl-u | Any other key closes'
endfunction

" Callback when popup closes - clear the echo message
function! s:PopupCallback(winid, result)
    echo ''
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

" ============================================================================
" Vim Popup Filter and Callbacks
" ============================================================================
"
" Filter function handles key presses in Vim popup windows
" - Scrolling keys (j/k, arrows, Ctrl-d/u) navigate content
" - All other keys close the popup

function! s:PopupFilter(winid, key) abort
    " Handle scrolling keys
    if s:IsScrollingKey(a:key)
        call s:HandleScrolling(a:winid, a:key)
        return 1
    endif
    
    " Any other key closes the popup
    call popup_close(a:winid)
    return 1
endfunction

" Check if the key is a scrolling key
function! s:IsScrollingKey(key)
    return a:key == 'j' || a:key == 'k' 
        \ || a:key == "\<Down>" || a:key == "\<Up>"
        \ || a:key == "\<C-D>" || a:key == "\<C-U>"
        \ || a:key == "\<PageDown>" || a:key == "\<PageUp>"
endfunction

" Handle scrolling in Vim popup
function! s:HandleScrolling(winid, key)
    let pos = popup_getpos(a:winid)
    let total_lines = line('$', a:winid)
    
    if a:key == 'j' || a:key == "\<Down>"
        call s:ScrollDown(a:winid, pos, total_lines)
    elseif a:key == 'k' || a:key == "\<Up>"
        call s:ScrollUp(a:winid, pos)
    elseif a:key == "\<C-D>" || a:key == "\<PageDown>"
        call s:PageDown(a:winid, pos, total_lines)
    elseif a:key == "\<C-U>" || a:key == "\<PageUp>"
        call s:PageUp(a:winid, pos)
    endif
endfunction

" Scroll down one line
function! s:ScrollDown(winid, pos, total_lines)
    if a:pos.lastline < a:total_lines
        call popup_setoptions(a:winid, {'firstline': a:pos.firstline + 1})
    endif
endfunction

" Scroll up one line
function! s:ScrollUp(winid, pos)
    if a:pos.firstline > 1
        call popup_setoptions(a:winid, {'firstline': a:pos.firstline - 1})
    endif
endfunction

" Scroll down one page
function! s:PageDown(winid, pos, total_lines)
    let pagesize = a:pos.lastline - a:pos.firstline
    if a:pos.lastline < a:total_lines
        call popup_setoptions(a:winid, {'firstline': a:pos.firstline + pagesize})
    endif
endfunction

" Scroll up one page
function! s:PageUp(winid, pos)
    let pagesize = a:pos.lastline - a:pos.firstline
    let new_firstline = max([1, a:pos.firstline - pagesize])
    call popup_setoptions(a:winid, {'firstline': new_firstline})
endfunction

" ============================================================================
" Commands and Keybindings
" ============================================================================

" Dictionary lookup commands
command! -nargs=? RobertDict call s:ShowDefinition(<q-args>)
command! -nargs=? R call s:ShowDefinition(<q-args>)
command! -nargs=? Dict call s:ShowDefinition(<q-args>)

" Reading mode toggle command
command! RobertReadingMode call RobertToggleReadingMode()

" Key mappings
" FAST ACCESS - Choose your favorite:

" Option 1: Leader key (default \ then d)
nnoremap <leader>d :RobertDict<CR>

" Option 2: Double-tap comma (super fast!)
nnoremap ,, :RobertDict<CR>

" Option 3: K in normal mode (replaces default man page lookup)
" nnoremap K :RobertDict<CR>

" Option 4: Function key F2
" nnoremap <F2> :RobertDict<CR>

" Reading mode toggle
" nnoremap <leader>r :RobertReadingMode<CR>