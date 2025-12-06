local M = {}

-- Get the sentence around the cursor (handles multi-line sentences)
function M.get_current_sentence()
	local current_line_num = vim.fn.line('.')
	local col = vim.fn.col('.')
	
	-- Get the full paragraph (lines between empty lines)
	local start_line = current_line_num
	local end_line = current_line_num
	
	-- Search upward for empty line or buffer start
	while start_line > 1 and vim.fn.getline(start_line - 1):match('%S') do
		start_line = start_line - 1
	end
	
	-- Search downward for empty line or buffer end
	local last_line = vim.fn.line('$')
	while end_line < last_line and vim.fn.getline(end_line + 1):match('%S') do
		end_line = end_line + 1
	end
	
	-- Get all lines in the paragraph
	local lines = vim.fn.getline(start_line, end_line)
	local paragraph = table.concat(lines, ' ')
	
	-- Calculate character position in the paragraph
	local char_pos = 0
	for i = start_line, current_line_num - 1 do
		char_pos = char_pos + #vim.fn.getline(i) + 1  -- +1 for space
	end
	char_pos = char_pos + col
	
	-- Find sentence boundaries in the paragraph
	local before = paragraph:sub(1, char_pos)
	local after = paragraph:sub(char_pos)
	
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
	
	local sentence = paragraph:sub(char_pos - sent_start_offset + 1, char_pos + sent_end_offset)
	return sentence:gsub('^%s+', ''):gsub('%s+$', '')
end

-- Get the paragraph around the cursor (lines between empty lines)
function M.get_current_paragraph()
	local current_line = vim.fn.line('.')
	local start_line = current_line
	local end_line = current_line
	
	-- Search upward for empty line
	while start_line > 1 and vim.fn.getline(start_line - 1):match('%S') do
		start_line = start_line - 1
	end
	
	-- Search downward for empty line
	local last_line = vim.fn.line('$')
	while end_line < last_line and vim.fn.getline(end_line + 1):match('%S') do
		end_line = end_line + 1
	end
	
	-- Join lines with spaces
	local lines = vim.fn.getline(start_line, end_line)
	return table.concat(lines, ' ')
end

return M

