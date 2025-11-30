if vim.g.loaded_quick_notes then
	return
end
vim.g.loaded_quick_notes = true

vim.api.nvim_create_user_command("Note", function(opts)
	require("quick-notes").create_note(opts.args)
end, {
	nargs = "?",
	desc = "Create a new timestamped note",
})
