# google-doc-watcher

#Install:

1. Clone into $HOME/google-doc-watcher

2. Edit $HOME/.google-doc-docwatcherrc

3. run $HOME/google-doc-watcher/google-doc-watcher
   - Upon first run will email you the full diff. Call it bug or feature
	 that's what it is.

4. Run once per hour:
    0 * * * *       $HOME/google-doc-watcher/google-doc-watcher -q --smtp-host your-smtp-host --smtp-user user --smtp-pass secret

#Note:
When run twice in the same minute, it re-downloads all file formats but
does not send a diff email.
