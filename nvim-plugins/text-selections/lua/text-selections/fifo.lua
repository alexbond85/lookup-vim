local M = {}

-- Send selection data to Python service via FIFO
function M.send(config, data)
	local json = vim.fn.json_encode(data)
	
	-- Write to FIFO using async job to avoid blocking
	-- Using writefile is more reliable than shell echo for JSON with newlines
	vim.schedule(function()
		-- Try to write to FIFO, ignore errors if nobody is listening
		pcall(function()
			local file = io.open(config.fifo_path, 'w')
			if file then
				file:write(json .. '\n')
				file:close()
			end
		end)
	end)
end

return M

