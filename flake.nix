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
          pip

          # Image processing & metadata
          pillow
          exifread
          opencv4
          numpy

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
