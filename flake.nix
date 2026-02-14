{
  description = "hackncstate-2026-gopals-chosen — React 19 + Vite 7 dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          name = "hackncstate-2026";

          packages = with pkgs; [
            nodejs_22   # Node.js 22.22.0
            nodePackages.npm
          ];

          shellHook = ''
            echo "Node $(node --version) | npm $(npm --version)"
            echo "Run 'cd my-react-app && npm install && npm run dev' to start."
          '';
        };
      });
}
