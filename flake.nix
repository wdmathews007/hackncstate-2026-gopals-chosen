{
  description = "Smoke and Mirrors";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          # Backend framework
          fastapi
          fastapi-cli
          uvicorn
          python-multipart
          python-dotenv

          # Image processing & metadata
          pillow
          exifread
          opencv4
          numpy
          (ps.buildPythonPackage rec {
            pname = "iptcinfo3";
            version = "2.3.0";
            pyproject = true;
            src = ps.fetchPypi {
              inherit pname version;
              sha256 = "aee2ee68b6b77aa6e317eed956ff36affc7dfba033c95458026815fa41b4a5e6";
            };
            build-system = with ps; [ hatchling ];
            doCheck = false;
          })

          # ML inference
          torch
          torchvision
          grad-cam

          # External APIs & HTTP
          google-cloud-vision
          httpx
          requests
          praw
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            nodejs_22
            nodePackages.npm
            pythonEnv
          ];
        };
      });
}
