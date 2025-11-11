" Robert Dictionary Vim Plugin
" Usage:
"   :RobertDict           - Look up word under cursor
"   :RobertDict maison    - Look up specific word
"   <leader>d             - Quick lookup word under cursor (normal mode)
"
" Popup appears above the cursor. To scroll and navigate:
"   j/k or ↓/↑            - Scroll line by line
"   Ctrl-d/Ctrl-u         - Page down/up
"   q or Esc              - Close popup

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
        call nvim_win_set_option(win, 'winhl', 'Normal:Pmenu')
        
        " Set buffer options
        setlocal buftype=nofile
        setlocal bufhidden=wipe
        setlocal nomodifiable
        setlocal noswapfile
        
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
            \ 'filter': 's:PopupFilter'
            \ })
        
        echo 'Scroll: j/k | Page: Ctrl-d/Ctrl-u | Close: q or Esc'
    endif
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

" Define the command with optional argument
command! -nargs=? RobertDict call s:ShowDefinition(<q-args>)

" Optional: Add a key mapping (e.g., <leader>d for definition on cursor word)
nnoremap <leader>d :RobertDict<CR>