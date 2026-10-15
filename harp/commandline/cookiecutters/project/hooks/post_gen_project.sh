#! /bin/bash

if [ "{{cookiecutter.create_application}}" == "False" ]; then
    rm -rf ./{{cookiecutter.__pkg_name}}
fi


if [ "{{cookiecutter.create_config}}" == "False" ]; then
    rm -f ./config.yml
fi

# Initialize git repository if git is available
if command -v git &> /dev/null; then
    git init
    git add .
    GIT_AUTHOR_NAME='{{ cookiecutter.author_name | replace("'", "'\\''") }}' \
    GIT_AUTHOR_EMAIL='{{ cookiecutter.author_email | replace("'", "'\\''") }}' \
    GIT_COMMITTER_NAME='{{ cookiecutter.author_name | replace("'", "'\\''") }}' \
    GIT_COMMITTER_EMAIL='{{ cookiecutter.author_email | replace("'", "'\\''") }}' \
    git commit -m "chore: initial project generation"
fi

echo 'Congratulations, your HARP project «{{ cookiecutter.name | replace("'", "'\\''") }}» has been created in «{{ cookiecutter.__dir_name }}».'
echo
echo "To install the project dependencies, run '(cd {{cookiecutter.__dir_name}} && make install)'."
echo "To run the tests, run '(cd {{cookiecutter.__dir_name}} && make test)'."
echo "To start your project, run '(cd {{cookiecutter.__dir_name}} && make start)'."
