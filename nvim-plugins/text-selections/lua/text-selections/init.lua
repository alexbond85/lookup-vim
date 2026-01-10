--[[
Text Selections Plugin - Select text and send it for external processing.

Two main functions:
1. Capture: yank text → send to FIFO (with surrounding context) for processing
2. Display: load past selections from JSONL cache → highlight in buffer

Toggle "highlight mode" to enable both: shows historical selections as
underlined text, and enables capture workflow (visual select → ",," → sends to FIFO).

Defaults to .cache/ in project root; override via setup({cache_dir = "..."}).
--]]

local M = {}

local context = require('text-selections.context')
local fifo = require('text-selections.fifo')

-- Derive project root from this file's location
-- debug.getinfo(1).source returns "@/path/to/init.lua", :sub(2) strips the "@"
local this_file = debug.getinfo(1).source:sub(2)
-- :p = full path, :h = parent dir (first :h strips init.lua, then ×4 more to reach project root)
local project_root = vim.fn.fnamemodify(this_file, ":p:h:h:h:h:h")

--- Parse INI file and return table of {section = {key = value}}
local function parse_ini(filepath)
	local config = {}
	local current_section = nil
	local file = io.open(filepath, "r")
	if not file then return config end
	
	for line in file:lines() do
		-- Skip comments and empty lines
		line = line:match("^%s*(.-)%s*$")  -- trim
		if line ~= "" and not line:match("^[#;]") then
			-- Section header: [section]
			local section = line:match("^%[(.+)%]$")
			if section then
				current_section = section
				config[section] = config[section] or {}
			-- Key = value
			elseif current_section then
				local key, value = line:match("^([^=]+)%s*=%s*(.*)$")
				if key and value then
					config[current_section][key:match("^%s*(.-)%s*$")] = value
				end
			end
		end
	end
	file:close()
	return config
end

-- Read paths from config.ini (shared with Python client)
local ini = parse_ini(project_root .. "/config.ini")
local paths = ini.paths or {}

local cache_dir = project_root .. "/" .. (paths.cache_dir or ".cache")
local fifo_name = paths.fifo_file or "nvim-selection.fifo"
local selections_name = paths.selections_file or "selections.jsonl"

M.config = {
	cache_dir = cache_dir,
	fifo_path = cache_dir .. "/" .. fifo_name,
	selections_file = cache_dir .. "/" .. selections_name,
}

-- Namespace isolates our highlights from other plugins
M.ns_id = vim.api.nvim_create_namespace("text_selections")
M.highlight_mode = false
M.original_visual_hl = nil

--- Remap 'v' for faster word selection while in highlight mode.
--- Called: when highlight_mode turns ON
--- Effect: 'v' in normal → select word; 'v' in visual → extend to word end
function M.setup_word_selection()
	vim.keymap.set('n', 'v', 'viw', { 
		buffer = true,  -- only in current buffer, not global
		desc = "Visual select inner word (auto-select mode)"  -- shown in :map and which-key
	})
	vim.keymap.set('v', 'v', 'e', {
		buffer = true,
		desc = "Move to end of word in visual mode"
	})
end

--- Restore default 'v' behavior.
--- Called: when highlight_mode turns OFF
--- Effect: removes buffer-local 'v' remaps
function M.teardown_word_selection()
	pcall(vim.keymap.del, 'n', 'v', { buffer = true })
	pcall(vim.keymap.del, 'v', 'v', { buffer = true })
end

--- Initialize plugin (optional, defaults are set above).
--- Called: once at Neovim startup (in plugin config)
--- Effect: overrides config if opts provided, creates cache dir, stores original Visual hl
function M.setup(opts)
	opts = opts or {}
	
	-- Override defaults if cache_dir provided
	if opts.cache_dir then
		local cache_dir = vim.fn.expand(opts.cache_dir)
		M.config = {
			cache_dir = cache_dir,
			fifo_path = cache_dir .. "/" .. FIFO_NAME,
			selections_file = cache_dir .. "/" .. SELECTIONS_NAME,
		}
	end
	
	-- Ensure cache directory exists ("p" = create parents if needed)
	vim.fn.mkdir(M.config.cache_dir, "p")
	
	-- Create empty selections.jsonl if it doesn't exist
	if vim.fn.filereadable(M.config.selections_file) == 0 then
		vim.fn.writefile({}, M.config.selections_file)
	end
	
	-- Create FIFO if it doesn't exist (mkfifo creates a named pipe)
	if vim.fn.filereadable(M.config.fifo_path) == 0 then
		os.execute("mkfifo " .. vim.fn.shellescape(M.config.fifo_path))
	end
	
	-- Save current Visual highlight so we can restore it when mode turns OFF
	M.original_visual_hl = vim.api.nvim_get_hl(0, {name = "Visual"})
end

--- Toggle highlight mode on/off.
--- Called: by user keymap (e.g., <leader>h)
--- Effect ON: load cached selections, underline Visual hl, enable word selection
--- Effect OFF: clear highlights, restore Visual hl, disable word selection
function M.toggle_highlight_mode()
	if not M.config.selections_file then
		vim.notify("text-selections: setup() must be called before using this plugin", vim.log.levels.ERROR)
		return
	end
	
	if not M.original_visual_hl then
		M.original_visual_hl = vim.api.nvim_get_hl(0, {name = "Visual"})
	end
	
	M.highlight_mode = not M.highlight_mode
	
	if M.highlight_mode then
		vim.notify("Text highlight mode: ON", vim.log.levels.INFO)
		M.load_and_highlight()
		local modified_hl = vim.tbl_deep_extend("force", M.original_visual_hl, {underline = true})
		vim.api.nvim_set_hl(0, "Visual", modified_hl)
		M.setup_word_selection()
	else
		vim.notify("Text highlight mode: OFF", vim.log.levels.INFO)
		vim.api.nvim_buf_clear_namespace(0, M.ns_id, 0, -1)
		if M.original_visual_hl then
			vim.api.nvim_set_hl(0, "Visual", M.original_visual_hl)
		end
		M.teardown_word_selection()
	end
end

--- Send yanked selection to Python lookup service.
--- Called: after yank in visual mode (via autocmd), only when highlight_mode is ON
--- Effect: highlights text immediately, sends selection + context to FIFO
function M.save_selection()
	if not M.highlight_mode then return end
	
	if not M.config.selections_file then
		vim.notify("text-selections: setup() not called", vim.log.levels.ERROR)
		return
	end
	
	-- Get from register as list (proper UTF-8 handling for multi-byte chars)
	local selected_lines = vim.fn.getreg('"', 1, true)
	local selected_text = table.concat(selected_lines, '\n')
	
	if selected_text == "" then
		vim.notify("No text in register", vim.log.levels.WARN)
		return
	end

	vim.notify("Selection sent to lookup!", vim.log.levels.INFO)
	M.highlight_text(selected_text)
	
	fifo.send(M.config, {
		selection = selected_text,
		phrase = context.get_current_sentence(),
		paragraph = context.get_current_paragraph(),
		file = vim.api.nvim_buf_get_name(0),
	})
end

--- Highlight all occurrences of text in current buffer.
--- Called: by save_selection() and load_and_highlight()
--- Effect: adds underline extmarks for all matches
function M.highlight_text(text)
	local buf = vim.api.nvim_get_current_buf()
	local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)

	if text:find('\n') then
		M.highlight_multiline_text(buf, lines, text)
		-- Also try with newlines as spaces (matches joined paragraph text)
		M.highlight_singleline_text(buf, lines, text:gsub('\n', ' '))
	else
		M.highlight_singleline_text(buf, lines, text)
	end
end

--- Find and underline all single-line occurrences of text.
function M.highlight_singleline_text(buf, lines, text)
	for line_num = 1, #lines do
		local line_text = lines[line_num]
		local start_col = 1

		while true do
			local col = string.find(line_text, text, start_col, true)
			if not col then break end

			pcall(vim.api.nvim_buf_set_extmark, buf, M.ns_id, line_num - 1, col - 1, {
				end_col = col - 1 + #text,
				hl_group = "Underlined",
			})
			start_col = col + #text
		end
	end
end

--- Find and underline multi-line text spanning consecutive lines.
function M.highlight_multiline_text(buf, lines, text)
	local text_lines = vim.split(text, '\n', {plain = true})
	if #text_lines > 0 and text_lines[#text_lines] == "" then
		table.remove(text_lines)
	end
	if #text_lines <= 1 then return end
	
	for start_line = 1, #lines - #text_lines + 1 do
		local match = true
		local match_positions = {}
		
		for i = 1, #text_lines do
			local match_pos = lines[start_line + i - 1]:find(text_lines[i], 1, true)
			if not match_pos then
				match = false
				break
			end
			match_positions[i] = match_pos
		end
		
		if match then
			for i = 1, #text_lines do
				local start_col = match_positions[i] - 1
				pcall(vim.api.nvim_buf_set_extmark, buf, M.ns_id, start_line + i - 2, start_col, {
					end_col = start_col + #text_lines[i],
					hl_group = "Underlined",
				})
			end
		end
	end
end

--- Load all cached selections and highlight them in current buffer.
--- Called: when highlight_mode turns ON
--- Effect: reads JSONL cache, underlines all previously saved selections
function M.load_and_highlight()
	if not M.highlight_mode or not M.config.selections_file then return end

	local file = io.open(M.config.selections_file, "r")
	if not file then return end

	local selections = {}
	local seen = {}
	
	for line in file:lines() do
		if line ~= "" then
			local ok, record = pcall(vim.json.decode, line)
			if ok and record.selection and record.selection ~= "" and not seen[record.selection] then
				table.insert(selections, record.selection)
				seen[record.selection] = true
			end
		end
	end
	file:close()

	vim.api.nvim_buf_clear_namespace(0, M.ns_id, 0, -1)
	for _, text in ipairs(selections) do
		M.highlight_text(text)
	end
end

return M
