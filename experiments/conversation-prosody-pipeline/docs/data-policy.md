# Data and artifact policy

Media datasets and generated artifacts are local experiment inputs and outputs,
not part of the Conversation Prosody Pipeline source distribution.

Do not commit:

- downloaded audio or video;
- converted WAV files;
- speech-to-text or other model files and caches; or
- bulk generated transcripts, metadata, reports, or other experiment outputs.

Keep local corpora and derived files under `import/`, which is ignored by Git
apart from its placeholder `.gitkeep`. If an experiment needs a different
location, add that location to `.gitignore` before creating or downloading the
files. Small, purpose-built test fixtures should be reviewed separately before
being tracked.

Lab notes may be committed, but they should record provenance rather than bundle
the source material. Include, when possible:

- the source page and direct media URL;
- the media's license or public-domain status, including where that status was
  verified;
- a cryptographic hash such as SHA-256 for each downloaded source file; and
- relevant retrieval dates, tool versions, and transformation settings.

For reproducible examples, use public-domain media, permissively licensed media,
or media owned by the contributor. Confirm that the applicable terms permit the
intended use; a publicly reachable file is not necessarily licensed for reuse.
