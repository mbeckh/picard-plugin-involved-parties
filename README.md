# Additional Involved Parties Details

![Latest Version](https://img.shields.io/github/v/tag/mbeckh/picard-plugin-involved-parties?sort=semver&filter=v*&style=flat-square&label=latest)
![Supports](https://img.shields.io/badge/dynamic/regex?url=https%3A%2F%2Fraw.githubusercontent.com%2Fmbeckh%2Fpicard-plugin-involved-parties%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&search=dependencies%5Cs*%3D%5Cs*%5C%5B%5B%5E%5D%5D*%22picard%5B%5E%22%5D*(%3E%3D.*%3F)%5B%2C%22%5D&replace=%241&flags=s&style=flat-square&label=picard&color=orange)
![Tested with](https://img.shields.io/badge/dynamic/regex?url=https%3A%2F%2Fraw.githubusercontent.com%2Fmbeckh%2Fpicard-plugin-involved-parties%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&search=dependencies%5Cs*%3D%5Cs*%5C%5B%5B%5E%5D%5D*%22picard%5B%5E%22%5D*(%3C%3D.*%3F)%5B%2C%22%5D&replace=%241&flags=s&style=flat-square&label=tested+with&color=green)

A plugin for [MusicBrainz Picard](https://picard.musicbrainz.org) that provides
additional metadata for composers, lyricists, writers and producers.

## What it Does

While [PICARD-2383](https://tickets.metabrainz.org/browse/PICARD-2383) added
musicbrainz_composerid, respective data is not yet available for other involved
parties.

The plugin adds the following multi-value metadata variables for each track if
the respective data is available:

* _aipd_composer_id
* _aipd_composer_legal
* _aipd_lyricist_id
* _aipd_lyricist_legal
* _aipd_producer_id
* _aipd_producer_legal
* _aipd_writer_id
* _aipd_writer_legal

If a legal name is not available, the plugin useses the default / standard name
from MusicBrainz.

Please note that the plugin makes additional API calls to the MusicBrainz
database and might therefore slow down retrieval. An internal memory cache is
used for the lookup of legal names.

## License

The code is released under the Apache License Version 2.0. Please see
[LICENSE](LICENSE) for details and [NOTICE](NOTICE) for the required information
when using picard-plugin-involved-parties in your own work.
