if vim.g.loaded_text_selections then
	return
end
vim.g.loaded_text_selections = true

-- Keymap to save selection (only works when highlight mode is ON)
vim.keymap.set("v", ",,", function()
	local selections = require("text-selections")
	-- Only save if highlight mode is active
	if selections.highlight_mode then
		-- Yank the selection and exit visual mode
		vim.cmd('normal! y')
		-- Then save it
		selections.save_selection()
	else
		-- If mode is off, just yank normally
		vim.cmd('normal! y')
	end
end, { desc = "Save text selection" })

-- Keymap to toggle highlight mode
vim.keymap.set("n", "<leader>th", function()
	require("text-selections").toggle_highlight_mode()
end, { desc = "Toggle text highlight mode" })

-- Command to toggle
vim.api.nvim_create_user_command("ToggleHighlights", function()
	require("text-selections").toggle_highlight_mode()
end, { desc = "Toggle text highlight mode" })

-- Auto-highlight on buffer change (only if mode is active)
vim.api.nvim_create_autocmd({ "BufEnter" }, {
	callback = function()
		require("text-selections").load_and_highlight()
	end,
})
