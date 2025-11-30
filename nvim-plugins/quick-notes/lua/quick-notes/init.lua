local M = {}

M.config = {
	notes_dir = vim.fn.expand("~/projects/alexbond/robert-online/books/notes"),
	date_format = "%Y-%m-%d-%H%M%S",
}

function M.setup(opts)
	M.config = vim.tbl_deep_extend("force", M.config, opts or {})
	vim.fn.mkdir(M.config.notes_dir, "p")
end

function M.create_note(title)
	local timestamp = os.date(M.config.date_format)
	local filename = string.format("%s/%s-%s.md", M.config.notes_dir, timestamp, title or "note")

	vim.cmd("edit " .. filename)

	-- Add template
	local lines = {
		"# " .. (title or "Note"),
		"",
		"Date: " .. os.date("%Y-%m-%d %H:%M:%S"),
		"",
		"",
	}
	vim.api.nvim_buf_set_lines(0, 0, -1, false, lines)
	vim.api.nvim_win_set_cursor(0, { #lines, 0 })
end

return M
