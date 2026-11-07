from kdehub.app import UPDATE_SCRIPTS, konsole_argv


def test_konsole_argv_holds_window_and_runs_script_via_bash():
    assert konsole_argv("sudo pacman -Syu") == ["konsole", "--hold", "-e", "bash", "-c", "sudo pacman -Syu"]


def test_update_menu_commands():
    assert list(UPDATE_SCRIPTS.values()) == [
        "sudo pacman -Syu",
        "yay -Syu",
        "npm update -g",
        "sudo pacman -Syu && yay -Sua && npm update -g",
    ]
