local M = {}

-- Get the sentence around the cursor
function M.get_current_sentence()
	local line = vim.fn.getline('.')
	local col = vim.fn.col('.')
	
	-- Find sentence boundaries (period, question mark, exclamation)
	local before = line:sub(1, col)
	local after = line:sub(col)
	
	local sent_start = before:reverse():find('[.!?]') or #before
	local sent_end = after:find('[.!?]') or #after
	
	return line:sub(col - sent_start + 1, col + sent_end):gsub('^%s+', ''):gsub('%s+$', '')
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

