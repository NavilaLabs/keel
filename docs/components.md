# Workflow-Komponenten: Agents, Hooks, Skills, State

Arbeitsstand (deutsch). Bezeichner, Dateinamen und Feldnamen sind bereits englisch und werden so übernommen; die tatsächlichen Definitionsdateien werden komplett auf Englisch geschrieben.

---

## 1. Orchestrator

**Slash-Command:** `/ticket <ticket-id>`

Kennt die Schrittreihenfolge, liest `state.json` und steigt **an der dort hinterlegten Stelle** ein – nicht bei Schritt 1. Ruft Agents, Skills und Artefakt-Schreibvorgänge an den passenden Stellen auf und respektiert die Zonen (Intake sequenziell, Blocks 6–7 parallel / 8–9 sequenziell, Delivery erst bei allen Blöcken `done`).

Damit sind Wiedereinstieg (11.2), Merge-Sync (12) und "morgen weitermachen" ohne Chat-Kontext abgedeckt.

Ergänzende Commands:

| Command | Zweck |
|---|---|
| `/ticket <id>` | Starten oder fortsetzen |
| `/sync-architecture <id>` | Schritt 12, manuell ausgelöst |
| `/ticket-status <id>` | `state.json` lesbar ausgeben (Vorstufe der späteren UI) |

---

## 2. Agents

Subagents bekommen einen eigenen, isolierten Kontext. Kriterium: viel Rohmaterial rein, wenig Kondensat raus. Bewusst **kein** Agent für Schritt 7 und für Rücksprache-Punkte – dort soll alles im Hauptkontext liegen, wo der Entwickler es sieht.

| Agent | Schritt | Input | Output |
|---|---|---|---|
| `context-gatherer` | 1 | Ticket + verwandte Tickets + PR-Kommentare (Jira/GitHub/Bitbucket MCP), LikeC4-Ist-Modell, betroffener Code | Kondensierter Kontext-Report, keine Rohdaten |
| `research-agent` | 6.3 | Problembeschreibung des Blocks | Liste von Lösungsoptionen mit Quellen, ohne Suchrauschen |
| `review-triage` | 11.1 | PR-Kommentare | Strukturierte Liste: Kommentar → Wiedereinstiegspunkt (1/2/7/8/neues Ticket) |
| `ist-extractor` | 12.1 | Gemergter Code | Extrahierter Ist-Stand als `.c4`-Diff-Vorschlag gegen `main` |

---

## 3. Skills

Wiederverwendbares Wissen und Konventionen, ohne eigenen Kontext.

| Skill | Inhalt |
|---|---|
| `artifact-formats` | Aufbau von `knowledge.md`, ADR-Template, `state.json`-Schema |
| `likec4-conventions` | Dateistruktur, Naming, Disziplinregeln: nicht die ganze Codebase auf Component-Ebene modellieren, `description` kurz halten (1 Satz Verantwortung), `link` statt Duplizierung von Signaturen, ein File pro Container |
| `stub-conventions` | Was ein Stub je Sprache ist (Rust: Trait, PHP: Interface, Dart: Abstract Class, …) und dass der Vertrag – Fehlerverhalten, Idempotenz, Invarianten – in Doc-Comments gehört, nicht ins Diagramm |
| `decision-heuristics` | Die "lohnt sich das"-Regeln an einem Ort: Themenblock-Schnitt (4), ADR-Trigger (7.3: nur bei mehreren echten Optionen), kleine Korrektur vs. echter Rücksprung (Signatur/Beziehung geändert?), 8.0-Trigger |
| `consultation-protocol` | Wie eine Rücksprache formuliert, dargestellt und als Objekt in `state.json` abgelegt wird |

---

## 4. Hooks

Hooks sind die einzige Ebene, die tatsächlich **erzwingt** statt vorschlägt – und gleichzeitig die Event-Quelle für die spätere UI.

| Hook | Auslöser | Wirkung |
|---|---|---|
| `stub-lock` | Datei-Edit während Schritt 8/9 | Vergleicht gegen `stub_fingerprints` des aktiven Blocks. Signaturänderung → blockieren, Rücksprung 8→7 erzwingen. **Wichtigster Hook** – setzt die zentrale Regel des Workflows technisch durch |
| `consultation-gate` | Übergang zum nächsten Hauptpunkt in Zone Intake/Blocks bis 7 | Blockiert, solange keine Freigabe der zugehörigen Rücksprache in `state.json` steht |
| `ist-staleness` | Eintritt in Schritt 7 | Vergleicht `ist_base_commit` mit aktuellem `main` des Ticket-Repos. Bei Drift → Schritt 7.0 erzwingen |
| `block-overlap` | Schreiben von `claimed_components` (7.1) | Überschneidung mit Claims eines anderen Blocks → Rücksprung 7→4 |
| `sequential-implementation` | Eintritt in Schritt 8 | Blockiert, wenn bereits ein anderer Block in 8/9 aktiv ist |
| `pr-gate` | PR-Erstellung (10) | Blockiert, solange nicht alle Blöcke `done` sind oder Links zu `knowledge.md`, ADR(s) und `.c4`-View fehlen |
| `state-writer` | Nach jedem Schrittwechsel, jeder Rücksprache, jedem Rücksprung | Schreibt `state.json` fort; zugleich Event-Stream für die UI |

---

## 5. `state.json` (Schema-Skizze)

```json
{
  "ticket_id": "PROJ-1234",
  "phase": "intake | blocks | delivery",
  "ist_base_commit": "a1b2c3d",
  "artifacts": {
    "knowledge": "tickets/PROJ-1234/knowledge.md",
    "adrs": ["tickets/PROJ-1234/adr/0001-....md"],
    "c4_views": ["api-components"]
  },
  "blocks": [
    {
      "id": "block-1",
      "title": "...",
      "step": "7.2",
      "status": "in_progress | awaiting_consultation | done",
      "claimed_components": ["api.orderService"],
      "claimed_stubs": ["src/order/service.rs::OrderService"],
      "stub_fingerprints": {},
      "adrs": []
    }
  ],
  "consultations": [
    {
      "id": "c-001",
      "block": "block-1",
      "step": "7",
      "question": "...",
      "options": [],
      "answer": "...",
      "timestamp": "..."
    }
  ],
  "jump_log": [
    { "from": "8", "to": "7", "block": "block-1", "reason": "...", "timestamp": "..." }
  ]
}
```

Rücksprachen sind bewusst **Objekte mit ID**, kein Terminal-Text: nur so kann die spätere UI sie als Karte rendern, und es entsteht nebenbei das Audit-Log der Entscheidungen.

---

## 6. Blick auf die spätere UI

Die UI wird damit reine Darstellung über vorhandenen Daten, ohne Chatverlauf interpretieren zu müssen:

- `state.json` als Backend / Fortschrittsanzeige
- Hook-Events als Live-Stream
- `consultations[]` als interaktive Karten (Frage + Optionen + Antwort)
- `c4_views` als Diagramm-Ansicht
- `jump_log` als Historie, warum sich etwas geändert hat
