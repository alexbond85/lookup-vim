local M = {}

-- Get the sentence around the cursor (handles multi-line sentences)
function M.get_current_sentence()
	local current_line_num = vim.fn.line('.')
	local col = vim.fn.col('.')
	
	-- Get the full paragraph (lines between empty lines)
	local start_line = current_line_num
	local end_line = current_line_num
	
	local buf = vim.api.nvim_get_current_buf()
	
	-- Search upward for empty line or buffer start
	while start_line > 1 do
		local prev_line = vim.api.nvim_buf_get_lines(buf, start_line - 2, start_line - 1, false)[1]
		if not prev_line or not prev_line:match('%S') then
			break
		end
		start_line = start_line - 1
	end
	
	-- Search downward for empty line or buffer end
	local last_line = vim.api.nvim_buf_line_count(buf)
	while end_line < last_line do
		local next_line = vim.api.nvim_buf_get_lines(buf, end_line, end_line + 1, false)[1]
		if not next_line or not next_line:match('%S') then
			break
		end
		end_line = end_line + 1
	end
	
	-- Get all lines in the paragraph
	local lines = vim.api.nvim_buf_get_lines(buf, start_line - 1, end_line, false)
	local paragraph = table.concat(lines, ' ')
	
	-- Calculate byte position in the paragraph
	local byte_pos = 0
	for i = start_line, current_line_num - 1 do
		local line = vim.api.nvim_buf_get_lines(buf, i - 1, i, false)[1]
		byte_pos = byte_pos + #line + 1  -- +1 for space
	end
	byte_pos = byte_pos + col
	
	-- Find sentence boundaries in the paragraph
	local before = paragraph:sub(1, byte_pos)
	local after = paragraph:sub(byte_pos)
	
	-- Find last sentence ending before cursor (or start of paragraph)
	local sent_start_offset = 0
	for i = #before, 1, -1 do
		if before:sub(i, i):match('[.!?]') then
			sent_start_offset = #before - i
			break
		end
	end
	
	-- Find next sentence ending after cursor (or end of paragraph)
	local sent_end_offset = #after
	for i = 1, #after do
		if after:sub(i, i):match('[.!?]') then
			sent_end_offset = i
			break
		end
	end
	
	local sentence = paragraph:sub(byte_pos - sent_start_offset + 1, byte_pos + sent_end_offset)
	return sentence:gsub('^%s+', ''):gsub('%s+$', '')
end

-- Get the paragraph around the cursor (lines between empty lines)
function M.get_current_paragraph()
	local current_line = vim.fn.line('.')
	local start_line = current_line
	local end_line = current_line
	
	local buf = vim.api.nvim_get_current_buf()
	
	-- Search upward for empty line
	while start_line > 1 do
		local prev_line = vim.api.nvim_buf_get_lines(buf, start_line - 2, start_line - 1, false)[1]
		if not prev_line or not prev_line:match('%S') then
			break
		end
		start_line = start_line - 1
	end
	
	-- Search downward for empty line
	local last_line = vim.api.nvim_buf_line_count(buf)
	while end_line < last_line do
		local next_line = vim.api.nvim_buf_get_lines(buf, end_line, end_line + 1, false)[1]
		if not next_line or not next_line:match('%S') then
			break
		end
		end_line = end_line + 1
	end
	
	-- Join lines with spaces
	local lines = vim.api.nvim_buf_get_lines(buf, start_line - 1, end_line, false)
	return table.concat(lines, ' ')
end

return M
