# Concept trailer: "The Voice"

A 60-second concept trailer to explain Aimpire to developers and early collaborators. It is **concept footage, not gameplay**, and says so on screen. Everything it shows is either built, decided in an ADR, or marked as vision in the [vision](../vision.md).

## The idea

Most trailers show a world. This one follows **one message**. A god speaks a single sentence to one woman at night. She mishears part of it. Her council argues and decides what it meant. The world, not the god, decides what happens next. Then time accelerates: a second tribe, standing stones, cities, a launch, and finally a sky full of worlds.

That arc carries the whole pitch in order: minds that start knowing nothing; influence, not command; misunderstanding as a mechanic; consequences checked by a deterministic world; generations; the Great Filter; many worlds and, one day, their meeting.

**Audience:** engineers and technical players. Short, confident on-screen lines; no voice-over; no hype words we cannot back.

## Look and sound

- **Look:** a premium, modern god game. A living miniature world seen from a high three-quarter god's-eye camera, tilt-shift depth of field, hand-crafted low-poly terrain with a faint pixel texture, warm earth tones, cool blues for night and danger. Each tribe has one colour: ochre and teal.
- **UI:** added in the edit, not generated, so it is crisp and true to the design. Flat, Tufte-quiet panels: the channel buttons (Sign, Omen, Voice, Prayer), the voice box with its 280-character limit, the council's journal line, and the trace **sent → heard → reported → concluded → done**.
- **Sound:** each shot's own ambient sound (river, wind, fire, rain, crowd murmur), under one slow ambient pad. No music with lyrics; no narrator.

## Shot list

Generated with Google Veo 3.1 at 1080p, 16:9, 8 seconds per shot, native sound on. Every prompt ends with the same style and exclusion lines so the shots cut together.

| # | Time | Shot | On-screen overlay (added in the edit) |
|---|---|---|---|
| 0 | 0–3 s | Black | "Every god game gave you followers." → "We gave them minds." |
| 1 | 3–9 s | **Worlds.** Slow push through space past several small, different planets toward one blue-green world | "Generated worlds. Their own physics." |
| 2 | 9–16 s | **The camp.** God's-eye orbit over a tiny riverside camp at dusk; figures carry food to a fire | Journal: *"Day 40. The east grove is thinning. Send four to the river flats."* · label "Their council: a language model. It sees only what its people saw." |
| 3 | 16–22 s | **A sign.** A dark cloud forms over one dry valley; a column of rain falls; tiny figures look up | Channel bar, **SIGN · RAIN** lit · "You cannot command. You can only influence." |
| 4 | 22–29 s | **The voice.** Night. One woman wakes alone by the embers; the reeds bend in a wind that is not there; faint warm light on her face | **VOICE → one person** · typed: *"Wait for the river to fall before you cross."* · heard: *"…the river… cross…"* |
| 5 | 29–36 s | **The council.** The tribe around the fire, the woman speaking, others arguing, an elder pointing across the river | Trace lights up: sent → heard → reported → **concluded: "The sky tells us to cross."** → done · "They decide what you meant." |
| 6 | 36–43 s | **Generations.** Time-lapse over the same valley: huts become a village, standing stones carved with symbols rise, a second camp in teal appears across the river | "Generations remember. Records drift." · "A second tribe. A different model." |
| 7 | 43–50 s | **The filter.** From orbit, the night side of the world lit by cities; a rocket climbs through thin cloud on a pillar of fire | "Every civilization meets the Great Filter." |
| 8 | 50–56 s | **The hub.** A god's view of many small worlds in a dark void; two thin trails of light meet between two of them | "Many worlds. One day, they meet." |
| 9 | 56–62 s | Title | **AIMPIRE** · *Untrained AI sandbox. Tribes evolving in an infinitely generative universe.* · "Concept trailer, not gameplay. Open source · github.com/seedfourtytwo/aimpire" |

The developer beat sits between shots 2 and 3 as a 2-second card: **"Minds propose. A deterministic world decides. Every run replays."**

## Prompts

Shared ending, appended to every prompt:

> Style: a premium modern god-game render, like a high-end remake of a 1990s god game. Miniature living world, high three-quarter god's-eye camera, tilt-shift depth of field, soft global illumination, hand-crafted low-poly terrain with a subtle pixel texture, warm earth tones with cool night blues, crisp readable silhouettes. Cinematic, calm, awe-filled. No text, no letters, no user interface, no logos, no watermarks, no subtitles.

1. **Worlds.** A slow, steady camera push through deep space past four small planets, each a different world: one red and cratered, one ringed and amber, one white with ice, one violet with glowing seas. The camera glides between them toward a blue-green planet with oceans, one large river delta and swirling white clouds, which grows to fill the frame. Stars, soft nebula haze. Audio: a deep, slow ambient hum, faint shimmering tones, no music, no voices.
2. **The camp.** God's-eye camera slowly orbiting a tiny riverside camp at dusk on a grassy floodplain. A small group of about twenty tiny people in ochre clothing carry baskets of berries and fish to a central campfire; two people scrape hides; children run between low reed shelters. Smoke curls up; the river glints orange with the last light; a dense grove stands to the east. The people are small and seen from far above, like a living diorama. Audio: crackling fire, a gentle river, distant birds, soft indistinct murmur of voices, no music.
3. **A sign.** God's-eye view over a dry, cracked valley beside green hills. A single dark storm cloud forms quickly in the clear sky directly above the valley, and a narrow column of rain falls only on the valley while the sun still lights the hills around it. The cracked earth darkens; a few tiny people in ochre clothing at the valley edge stop working and look up at the sky, one raising an arm. Audio: rising wind, a low roll of thunder, the hiss of rain arriving, no music.
4. **The voice.** Night by a riverside camp, closer god's-eye view from above and to one side. Everyone sleeps around low glowing embers except one woman in an ochre cloak who wakes and sits up, alone. The tall reeds around her bend in a slow wave though nothing else moves, and a faint warm golden light falls on her face from above. She looks up, listening, startled and calm. Blue moonlight, soft fog over the water. Audio: near silence, crickets, a soft rush of wind through reeds, one deep resonant hum that swells and fades, no words, no music.
5. **The council.** Night, god's-eye view slowly descending toward a large campfire where about twenty tiny people in ochre clothing sit in a circle. The woman in the ochre cloak stands, speaking with her hands; some listeners nod, two men argue and shake their heads, an elder stands and points across the dark river to the far bank. Firelight flickers on faces, sparks rise. Audio: the fire, overlapping murmured voices in an unintelligible invented language, a raised voice, no music.
6. **Generations.** High god's-eye time-lapse over the same river valley: days and seasons flash past as light sweeps across the land. The riverside camp grows into a village of round huts with fields; a ring of standing stones rises on a hill, carved with simple symbols; a second camp with teal banners appears across the river and grows too; paths, a small bridge and smoke from many fires spread over the valley. Snow comes and goes, the river changes course slightly. Audio: a slow rising wash of wind and distant crowd sounds, a deep pulse, no music.
7. **The filter.** View from low orbit over the night side of a blue-green planet: coastlines and river valleys traced by clusters of warm city lights, a thin bright line of atmosphere at the horizon. The camera descends through thin clouds to find a single rocket climbing on a brilliant pillar of fire, its exhaust lighting the clouds orange. Audio: a distant deep roar that builds, wind, a low ominous swell, no music, no voices.
8. **The hub.** A slow, wide pull-back revealing a dark cosmic void filled with dozens of small glowing planets floating at different depths, each a different colour and climate, like jewels hung in space, gently rotating. Between two of them, two thin trails of light from tiny ships curve toward each other and meet in a soft flash. Audio: a vast airy ambient tone, faint chimes, a soft resolving swell, no music, no voices.

## Production plan and cost

The scripts and a step-by-step handoff for the agent that generates it are in `tools/trailer/` (start with `HANDOFF.md`).


| Item | Choice |
|---|---|
| Model | `google/veo-3.1` via OpenRouter, the strongest video model on the platform for realism and native sound |
| Settings | 1080p, 16:9, 8 s, `generate_audio: true`, fixed `seed` per shot |
| Price | $0.40 per second with audio: 8 shots × 8 s = **$25.60** |
| Budget | $35 cap: leaves about $9 for up to two retakes of weak shots |
| Edit | ffmpeg: trim each shot to its slot, crossfades, a generated ambient pad under the shots' own sound, overlays and cards rendered as images and composited |
| Label | "Concept trailer, not gameplay" on the end card, as the vision page requires |
