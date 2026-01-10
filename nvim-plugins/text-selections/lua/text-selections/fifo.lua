local M = {}

-- Remove invalid UTF-8 byte sequences from a string
local function clean_utf8(str)
	if type(str) ~= "string" then
		return str
	end
	
	local result = {}
	local i = 1
	local len = #str
	
	while i <= len do
		local byte = string.byte(str, i)
		
		if byte < 128 then
			-- ASCII: single byte
			table.insert(result, string.char(byte))
			i = i + 1
		elseif byte >= 194 and byte <= 223 then
			-- 2-byte sequence (C2-DF)
			if i + 1 <= len then
				local byte2 = string.byte(str, i + 1)
				if byte2 >= 128 and byte2 <= 191 then
					table.insert(result, string.sub(str, i, i + 1))
					i = i + 2
				else
					i = i + 1  -- Skip invalid
				end
			else
				i = i + 1  -- Skip incomplete
			end
		elseif byte >= 224 and byte <= 239 then
			-- 3-byte sequence (E0-EF)
			if i + 2 <= len then
				local byte2 = string.byte(str, i + 1)
				local byte3 = string.byte(str, i + 2)
				if byte2 >= 128 and byte2 <= 191 and byte3 >= 128 and byte3 <= 191 then
					table.insert(result, string.sub(str, i, i + 2))
					i = i + 3
				else
					i = i + 1  -- Skip invalid
				end
			else
				i = i + 1  -- Skip incomplete
			end
		elseif byte >= 240 and byte <= 244 then
			-- 4-byte sequence (F0-F4)
			if i + 3 <= len then
				local byte2 = string.byte(str, i + 1)
				local byte3 = string.byte(str, i + 2)
				local byte4 = string.byte(str, i + 3)
				if byte2 >= 128 and byte2 <= 191 and byte3 >= 128 and byte3 <= 191 and byte4 >= 128 and byte4 <= 191 then
					table.insert(result, string.sub(str, i, i + 3))
					i = i + 4
				else
					i = i + 1  -- Skip invalid
				end
			else
				i = i + 1  -- Skip incomplete
			end
		else
			-- Invalid start byte (80-BF, C0-C1, F5-FF) - skip
			i = i + 1
		end
	end
	
	return table.concat(result)
end

-- Send selection data to Python service via FIFO
function M.send(config, data)
	-- Clean all string fields to ensure valid UTF-8 for JSON encoding
	local clean_data = {}
	for k, v in pairs(data) do
		clean_data[k] = clean_utf8(v)
	end
	
	local json = vim.fn.json_encode(clean_data)
	
	-- Write to FIFO asynchronously to avoid blocking
	vim.schedule(function()
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
