local M = {}

-- Send selection data to Python service via FIFO
function M.send(config, data)
	local json = vim.fn.json_encode(data)
	
	-- Write to FIFO (non-blocking, ignore errors)
	local cmd = string.format('echo %s > %s 2>/dev/null &',
		vim.fn.shellescape(json),
		config.fifo_path)
	
	vim.fn.system(cmd)
end

return M

