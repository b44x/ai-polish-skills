# ai-skills

A curated collection of modular, production-ready AI agent skills (`SKILL.md` format) tailored for real-world workflows and services.

Every skill provides:
- A standardized `SKILL.md` definition with YAML frontmatter (progressive disclosure).
- Dependency-free Python 3 helper scripts that communicate via clean JSON.
- Output references and error specifications.

---

## Available Skills

| Skill | Description | Triggers / Keywords |
|---|---|---|
| [`biala-lista`](skills/biala-lista/SKILL.md) | Official Polish Ministry of Finance White List (*Biała Lista Podatników VAT*). Verify active VAT payer status, company registry details, and registered settlement bank accounts before B2B transfers. | NIP, REGON, VAT status, "sprawdź NIP", "biała lista", "rachunek na białej liście", split payment |
| [`inpost`](skills/inpost/SKILL.md) | InPost parcel tracking and Paczkomat parcel locker finder across Poland. Lookup locker details (address, 24/7 access, Strefa Łatwego Dostępu, photos) and find nearest lockers by GPS coordinates. | InPost, Paczkomat, "gdzie moja paczka", "status przesyłki InPost", "najbliższy paczkomat" |
| [`filmweb`](skills/filmweb/SKILL.md) | Polish film and TV series database (Filmweb.pl). Search titles, ratings, user reviews, cast, premiere dates, and VOD availability with prices in PLN. | Filmweb, ocena filmu, "gdzie obejrzę", "kto grał w", polskie recenzje, seriale |

---

## Validation

All skills must pass frontmatter and structure validation:

```bash
python3 scripts/validate_skills.py
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch strategy, PR workflow, and skill anatomy guidelines.
