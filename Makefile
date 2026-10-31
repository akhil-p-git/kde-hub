.PHONY: run test install
run:
	uv run kde-hub --show
test:
	uv run pytest -q
# Autostart on login and copy the config to ~/.config/kde-hub (edit it there).
install:
	mkdir -p ~/.config/kde-hub ~/.config/autostart
	test -f ~/.config/kde-hub/config.toml || cp config.toml ~/.config/kde-hub/config.toml
	printf '[Desktop Entry]\nType=Application\nName=KDE Hub\nExec=uv run --project $(CURDIR) kde-hub\n' > ~/.config/autostart/kde-hub.desktop
