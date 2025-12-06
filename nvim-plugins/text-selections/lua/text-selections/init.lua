local M = {}

-- Import modules
local context = require('text-selections.context')
local fifo = require('text-selections.fifo')

-- Config with defaults (cache_dir must be provided in setup)
M.config = {
	cache_dir = nil,
	fifo_path = nil,
	selections_file = nil,
}

-- Storage for highlight namespace and mode state
M.ns_id = vim.api.nvim_create_namespace("text_selections")
M.highlight_mode = false
M.original_visual_hl = nil  -- Store original Visual highlight

function M.setup_word_selection()
	-- Map 'v' to automatically select whole word in normal mode
	vim.keymap.set('n', 'v', 'viw', { 
		buffer = true, 
		desc = "Visual select inner word (auto-select mode)" 
	})
end

function M.teardown_word_selection()
	-- Restore normal 'v' behavior
	pcall(vim.keymap.del, 'n', 'v', { buffer = true })
end

function M.setup(opts)
	opts = opts or {}
	
	-- cache_dir is required
	if not opts.cache_dir then
		error("text-selections: cache_dir is required in setup()")
	end
	
	local cache_dir = vim.fn.expand(opts.cache_dir)
	
	-- Derive paths from cache_dir
	M.config = {
		cache_dir = cache_dir,
		fifo_path = cache_dir .. "/nvim-selection.fifo",
		selections_file = cache_dir .. "/selections.jsonl",
	}
	
	-- Ensure cache directory exists
	vim.fn.mkdir(cache_dir, "p")
	
	-- Ensure selections file exists
	if vim.fn.filereadable(M.config.selections_file) == 0 then
		vim.fn.writefile({}, M.config.selections_file)
	end
	
	-- Store original Visual highlight
	M.original_visual_hl = vim.api.nvim_get_hl(0, {name = "Visual"})
end

function M.toggle_highlight_mode()
	-- Check if setup has been called
	if not M.config.selections_file then
		vim.notify("text-selections: setup() must be called before using this plugin", vim.log.levels.ERROR)
		return
	end
	
	-- Capture original highlight BEFORE changing mode (only once, when first toggling ON)
	if not M.original_visual_hl then
		M.original_visual_hl = vim.api.nvim_get_hl(0, {name = "Visual"})
	end
	
	M.highlight_mode = not M.highlight_mode
	
	if M.highlight_mode then
		vim.notify("Text highlight mode: ON", vim.log.levels.INFO)
		M.load_and_highlight()
		
		-- Create modified visual highlight with underline
		local modified_hl = vim.tbl_deep_extend("force", M.original_visual_hl, {underline = true})
		vim.api.nvim_set_hl(0, "Visual", modified_hl)
		
		-- Enable automatic word selection in visual mode
		M.setup_word_selection()
	else
		vim.notify("Text highlight mode: OFF", vim.log.levels.INFO)
		-- Clear all highlights
		vim.api.nvim_buf_clear_namespace(0, M.ns_id, 0, -1)
		
		-- Restore original Visual highlight
		if M.original_visual_hl then
			vim.api.nvim_set_hl(0, "Visual", M.original_visual_hl)
		end
		
		-- Disable automatic word selection
		M.teardown_word_selection()
	end
end

function M.save_selection()
	-- Only save and highlight if mode is active
	if not M.highlight_mode then
		return
	end
	
	-- Check if setup has been called
	if not M.config.selections_file then
		vim.notify("text-selections: setup() not called", vim.log.levels.ERROR)
		return
	end
	
	-- Get text from the unnamed register (what was just yanked)
	local selected_text = vim.fn.getreg('"')
	
	if selected_text == "" then
		vim.notify("No text in register", vim.log.levels.WARN)
		return
	end

	-- Note: Python service handles saving to CSV file
	vim.notify("Selection sent to lookup!", vim.log.levels.INFO)

	-- Highlight the selection immediately (will be persisted after lookup)
	M.highlight_text(selected_text)
	
	-- Send to lookup service
	local data = {
		selection = selected_text,
		phrase = context.get_current_sentence(),
		paragraph = context.get_current_paragraph(),
		file = vim.api.nvim_buf_get_name(0),
	}
	fifo.send(M.config, data)
end

function M.highlight_text(text)
	local buf = vim.api.nvim_get_current_buf()
	local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)

	-- Check if text contains newlines (multi-line selection)
	if text:find('\n') then
		-- Try to highlight as multi-line first
		M.highlight_multiline_text(buf, lines, text)
		
		-- Also try highlighting with newlines replaced by spaces
		-- (this matches how context functions join lines)
		local text_with_spaces = text:gsub('\n', ' ')
		M.highlight_singleline_text(buf, lines, text_with_spaces)
	else
		-- Handle single-line selections (original logic)
		M.highlight_singleline_text(buf, lines, text)
	end
end

function M.highlight_singleline_text(buf, lines, text)
	-- Original single-line highlighting logic
	for line_num = 1, #lines do
		local line_text = lines[line_num]
		local start_col = 1

		while true do
			local col = string.find(line_text, text, start_col, true) -- plain text search
			if not col then
				break
			end

			-- Add extmark (0-indexed)
			pcall(vim.api.nvim_buf_set_extmark, buf, M.ns_id, line_num - 1, col - 1, {
				end_col = col - 1 + #text,
				hl_group = "Underlined",
			})

			start_col = col + #text
		end
	end
end

function M.highlight_multiline_text(buf, lines, text)
	-- Split the text by newlines, preserving empty lines
	local text_lines = vim.split(text, '\n', {plain = true})
	
	-- Remove empty trailing element if text ends with newline
	if #text_lines > 0 and text_lines[#text_lines] == "" then
		table.remove(text_lines)
	end
	
	if #text_lines == 0 or #text_lines == 1 then
		return  -- Not a multi-line selection
	end
	
	-- Search for the pattern across consecutive lines
	for start_line = 1, #lines - #text_lines + 1 do
		local match = true
		local match_positions = {}
		
		-- Check if all lines match
		for i = 1, #text_lines do
			local line_idx = start_line + i - 1
			local line_text = lines[line_idx]
			local match_pos = line_text:find(text_lines[i], 1, true)
			
			if not match_pos then
				match = false
				break
			end
			
			match_positions[i] = match_pos
		end
		
		if match then
			-- Highlight each line of the match
			for i = 1, #text_lines do
				local line_num = start_line + i - 1
				local start_col = match_positions[i] - 1  -- Convert to 0-indexed
				local end_col = start_col + #text_lines[i]
				
				pcall(vim.api.nvim_buf_set_extmark, buf, M.ns_id, line_num - 1, start_col, {
					end_col = end_col,
					hl_group = "Underlined",
				})
			end
		end
	end
end

function M.load_and_highlight()
	if not M.highlight_mode then
		return
	end
	
	-- Check if setup has been called
	if not M.config.selections_file then
		return
	end

	-- Read JSONL file and extract selections
	local file = io.open(M.config.selections_file, "r")
	if not file then
		return
	end

	local selections = {}
	local seen = {}  -- Track unique selections
	
	-- Parse JSONL: one JSON object per line
	for line in file:lines() do
		if line ~= "" then
			-- Decode JSON line
			local ok, record = pcall(vim.json.decode, line)
			if ok and record.selection then
				local selection = record.selection
				if selection and selection ~= "" and not seen[selection] then
					table.insert(selections, selection)
					seen[selection] = true
				end
			end
		end
	end
	file:close()

	-- Clear existing highlights
	vim.api.nvim_buf_clear_namespace(0, M.ns_id, 0, -1)

	-- Highlight all unique selections
	for _, text in ipairs(selections) do
		M.highlight_text(text)
	end
end

return M
