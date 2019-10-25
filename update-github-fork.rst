Sync the github repository with the gitlab repository.
===
2019-10-25

Setup
-----
To be done **once**: set the upstream of the github to the gitlab:
git remote -v
git remote add upstream https://gitlab.com/hkex/pyr2


Update
------
git fetch upstream
git checkout master
git merge upstream/master
git push


