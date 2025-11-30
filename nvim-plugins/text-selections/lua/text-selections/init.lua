local M = {}

M.config = {
	selections_file = vim.fn.expand("~/projects/alexbond/robert-online/books/notes/selections.txt"),
}

-- Storage for highlight namespace and mode state
M.ns_id = vim.api.nvim_create_namespace("text_selections")
M.highlight_mode = false
M.original_visual_hl = nil  -- Store original Visual highlight

function M.setup(opts)
	M.config = vim.tbl_deep_extend("force", M.config, opts or {})
	
	-- Ensure directory exists
	local dir = vim.fn.fnamemodify(M.config.selections_file, ":h")
	vim.fn.mkdir(dir, "p")
	
	-- Ensure file exists
	if vim.fn.filereadable(M.config.selections_file) == 0 then
		vim.fn.writefile({}, M.config.selections_file)
	end
	
	-- Store original Visual highlight
	M.original_visual_hl = vim.api.nvim_get_hl(0, {name = "Visual"})
end

function M.toggle_highlight_mode()
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
	else
		vim.notify("Text highlight mode: OFF", vim.log.levels.INFO)
		-- Clear all highlights
		vim.api.nvim_buf_clear_namespace(0, M.ns_id, 0, -1)
		
		-- Restore original Visual highlight
		if M.original_visual_hl then
			vim.api.nvim_set_hl(0, "Visual", M.original_visual_hl)
		end
	end
end

function M.save_selection()
	-- Only save and highlight if mode is active
	if not M.highlight_mode then
		return
	end
	
	-- Get text from the unnamed register (what was just yanked)
	local selected_text = vim.fn.getreg('"')
	
	if selected_text == "" then
		vim.notify("No text in register", vim.log.levels.WARN)
		return
	end

	-- Append to file
	local file = io.open(M.config.selections_file, "a")
	if file then
		file:write(selected_text .. "\n")
		file:close()
		vim.notify("Selection saved!", vim.log.levels.INFO)
	else
		vim.notify("Failed to open selections file", vim.log.levels.ERROR)
		return
	end

	-- Highlight the saved selection
	M.highlight_text(selected_text)
end

function M.highlight_text(text)
	local buf = vim.api.nvim_get_current_buf()
	local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)

	-- Escape special pattern characters for plain text search
	local escaped = text:gsub("([%.%*%+%-%?%[%]%^%$%(%)%%])", "%%%1")

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

function M.load_and_highlight()
	if not M.highlight_mode then
		return
	end

	-- Read all selections
	local file = io.open(M.config.selections_file, "r")
	if not file then
		return
	end

	local selections = {}
	for line in file:lines() do
		if line ~= "" then
			table.insert(selections, line)
		end
	end
	file:close()

	-- Clear existing highlights
	vim.api.nvim_buf_clear_namespace(0, M.ns_id, 0, -1)

	-- Highlight all selections
	for _, text in ipairs(selections) do
		M.highlight_text(text)
	end
end

return M
