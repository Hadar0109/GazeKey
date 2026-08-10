# Prediction word list

## File

`words_en.txt` — frequency-ordered English words (one word per line; earlier =
higher priority). ~46k alphabetic ASCII words filtered for typing completion.

## Source

- **Name**: FrequencyWords (2018 English `en_50k.txt`)
- **URL**: https://github.com/hermitdave/FrequencyWords
- **Derived from**: OpenSubtitles2018 tokenized corpus
  (http://opus.nlpl.eu/OpenSubtitles2018.php)
- **Processing**: took frequency-ranked tokens; kept lowercase ASCII alphabetic
  words only; dropped counts; deduplicated while preserving frequency order

## License

- **Content**: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
  (FrequencyWords README: “CC-by-sa-4.0 for content”)
- **Code in that repo**: MIT (not bundled here)

## Attribution

Word frequencies derived from FrequencyWords by Hermit Dave / contributors,
licensed under Creative Commons Attribution-ShareAlike 4.0 International.
Original OpenSubtitles corpus attribution applies via that project.
