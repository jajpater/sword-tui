{
  description = "Bible TUI application using SWORD/diatheke backend";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        sword-tui = pkgs.python3Packages.buildPythonApplication {
          pname = "sword-tui";
          version = "0.1.0";
          src = ./.;
          format = "pyproject";

          nativeBuildInputs = with pkgs.python3Packages; [
            hatchling
          ];

          propagatedBuildInputs = with pkgs.python3Packages; [
            textual
            pyperclip
          ];

          # Make diatheke available at runtime
          # diatheke is part of the sword package
          makeWrapperArgs = [
            "--prefix" "PATH" ":" "${pkgs.sword}/bin"
          ];

          postInstall = ''
            # Install desktop file
            install -Dm644 $src/desktop/sword-tui.desktop $out/share/applications/sword-tui.desktop

            # Install icon
            install -Dm644 $src/desktop/sword-tui.svg $out/share/icons/hicolor/scalable/apps/sword-tui.svg
          '';

          meta = with pkgs.lib; {
            description = "Bible TUI application using SWORD/diatheke backend";
            homepage = "https://github.com/jajpater/sword-tui";
            license = licenses.mit;
            maintainers = [];
          };
        };
      in
      {
        packages = {
          default = sword-tui;
          sword-tui = sword-tui;
        };

        apps.default = {
          type = "app";
          program = "${sword-tui}/bin/sword-tui";
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python3
            python3Packages.textual
            python3Packages.pyperclip
            python3Packages.pytest
            python3Packages.pytest-asyncio
            sword  # provides diatheke
          ];
        };
      }
    );
}
