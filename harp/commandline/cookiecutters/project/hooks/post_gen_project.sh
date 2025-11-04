#! /bin/bash

if [ "{{cookiecutter.create_application}}" == "False" ]; then
    rm -rf ./{{cookiecutter.__pkg_name}}
fi


if [ "{{cookiecutter.create_config}}" == "False" ]; then
    rm -f ./config.yml
fi

echo "Congratulations, your HARP project «{{cookiecutter.name}}» has been created in «{{cookiecutter.__dir_name}}»."
echo
echo "To install the project dependencies, run '(cd {{cookiecutter.__dir_name}} && make install)'."
echo "To run the tests, run '(cd {{cookiecutter.__dir_name}} && make test)'."
echo "To start your project, run '(cd {{cookiecutter.__dir_name}} && make)'."
