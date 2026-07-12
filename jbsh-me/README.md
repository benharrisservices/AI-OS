# jbsh.me

A cinematic web experience. A personal operating manual for life, made as a gift from Ben to James.

Less website. More museum installation. Every chapter can be read, or heard.

**Live domain:** [jbsh.me](https://jbsh.me)

## Tech Stack

- Next.js 16 (App Router)
- TypeScript
- Tailwind CSS v4
- shadcn/ui
- Framer Motion
- Lucide Icons
- Vercel

## Getting Started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

**Password:** `poloko`

```bash
npm run build   # production build
npm start       # serve the build
npm run lint    # lint
```

## Structure

```
jbsh-me/
├── src/
│   ├── app/                  # layout, page, styles, icon
│   ├── components/
│   │   ├── audio/            # AudioControl, Waveform, Transcript
│   │   ├── gate/             # password gate
│   │   ├── welcome/          # one-time narrated intro
│   │   ├── sections/         # hero, narrative, feature, letter
│   │   ├── keys/             # credential card
│   │   ├── site/             # shell + left navigation
│   │   ├── easter-eggs/      # hidden interactions
│   │   ├── providers/        # theme provider
│   │   └── theme-switch.tsx  # iPhone-style toggle
│   ├── content/              # all copy and data
│   ├── hooks/                # useNarration
│   └── lib/                  # constants, audio path, utils
├── public/
│   ├── audio/                # one narration file per chapter
│   └── og-image.png
├── voice/                    # ElevenLabs scripts, one per chapter
└── README.md
```

## Audio

Every chapter binds to `/public/audio/{id}.mp3` through `src/lib/audio.ts`.
The bundled files are silent placeholders of realistic length.

To use real narration, export each chapter from ElevenLabs and replace the
matching file, keeping the same name. No code changes are required.

| Chapter | File |
|---|---|
| Identity | `audio/identity.mp3` |
| The Keys | `audio/keys.mp3` |
| The Principles | `audio/principles.mp3` |
| Freedom | `audio/freedom.mp3` |
| Learning | `audio/learning.mp3` |
| Health | `audio/health.mp3` |
| Money | `audio/money.mp3` |
| Business | `audio/business.mp3` |
| Technology | `audio/technology.mp3` |
| Artificial Intelligence | `audio/ai.mp3` |
| Leverage | `audio/leverage.mp3` |
| Books | `audio/books.mp3` |
| Projects | `audio/projects.mp3` |
| Useful Resources | `audio/resources.mp3` |
| Final Letter | `audio/letter.mp3` |

The transcript highlights each line in time with playback, weighted by line
length, so timing stays sensible for any file you drop in.

Scripts for each chapter live in `/voice`, ready to paste into ElevenLabs.

## Reusable Components

- `useNarration` binds one audio element and exposes play state, progress, and seek.
- `AudioControl` is the understated per-chapter player: play, time, waveform.
- `Waveform` is the subtle visualiser and scrubber.
- `Transcript` highlights the active line as audio plays.
- `ThemeSwitch` is the tiny sliding light and dark toggle.
- `CredentialCard` shows keys, hiding only passwords behind an eye icon.
- `NarratedSection` composes a full chapter: header, audio, transcript, body.

## Easter Eggs

| Interaction | Result |
|---|---|
| Double-click the word "James" | "Keep going." |
| Hold Shift for a few seconds | A faint constellation |
| Press J | A hidden line, softly |

## Deployment

```bash
npx vercel
```

Or import the GitHub repo in Vercel. No environment variables are required.

## License

Private. Made with care.

---

Built in a single sitting. Meant to feel like months.
