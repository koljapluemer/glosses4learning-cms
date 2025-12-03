You see here a COMPLETELY empty project folder.
Create a basic Flask CMS.
It should NOT use any kind of database, but directly treat folders in data/ as SSoT.

The main concept is to model glosses (for language learning) with a similar shape to this Django model:

```
class Gloss(models.Model):
    content = models.TextField()
    language = models.ForeignKey("Language", on_delete=models.CASCADE)
    transcriptions = models.JSONField(default=list)

    contains = models.ManyToManyField("self", related_name="contained_by", symmetrical=False, blank=True)
    near_synonyms = models.ManyToManyField("self", symmetrical=True, blank=True)
    near_homophones = models.ManyToManyField("self", symmetrical=True, blank=True)
    translations = models.ManyToManyField("self", symmetrical=True, blank=True)
    clarifies_usage = models.ManyToManyField("self", related_name="usage_of_clarified", symmetrical=False, blank=True)
    to_be_differentiated_from = models.ManyToManyField("self", symmetrical=True, blank=True)
    collocations = models.ManyToManyField("self", symmetrical=True, blank=True)
```

- use 3-letter ISO codes to refer to language
- create a JSON schema Draft-2020-12 for the gloss files (one gloss, one file)
- filenames should be equivalent to the content, removing (not replacing) every character that is actually illegal in filenames (slug)
- create folder per (needed) language code, directly place files in there
- `content` is the only actually required field
- refer to other glosses in the many to many relationships with a plain string in the format `$iso_code:$slug`, e.g. `"eng:I run"`
- split the flask app into modules/classes/files so that it's well understandable and well readable
- use the `uv`!!!! package manager throughout
- use plain html files for managing, make a default layout; use tailwind + daisy UI via CDN and avoid manual CSS as much as possible
- for now, just allow basic CRUD for glosses