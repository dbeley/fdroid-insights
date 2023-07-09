with import <nixpkgs> { };

let
  pythonPackages = python3Packages;
in pkgs.mkShell rec {
  name = "fdroidStatsPythonEnv";
  buildInputs = [
    pythonPackages.python

    pythonPackages.pandas
    pythonPackages.pygithub
    pythonPackages.python-gitlab
    pythonPackages.datasette
    csvs-to-sqlite
  ];

}
