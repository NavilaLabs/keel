# Entwicklungs-Workflow

## Grundprinzipien

- **Sprachunabhängig.** Alles, was "Stub" heißt, meint je nach Zielsprache Trait (Rust), Interface (PHP), Abstract Class (Dart) etc. Der Workflow definiert *was* passieren muss, nicht *wie*.
- **Rücksprache** wird nach jedem Hauptpunkt (nicht Unterpunkten) gehalten – außer explizit als "keine Rücksprache" markiert. Rücksprache = manueller Check durch den Entwickler, dass alles korrekt verstanden/definiert wurde.
- **Ab Schritt 8 (Implementierung) keine planmäßige Rücksprache mehr** – außer durch einen Rücksprung ausgelöst (siehe unten).
- **Artefakte liegen ausschließlich im Ticket-Repo, nie im Code-Repo.** Verknüpfung erfolgt nur über Links (Ticket ↔ Ticket-Repo ↔ Code-Repo-PR).
- **Ein Ticket-Repo pro Projekt** (FrachtPilot, Anagraph, Kimai-App, …).
- **Parallelität:** Themenblöcke laufen **parallel bis einschließlich Schritt 7**, ab Schritt 8 **sequenziell** (ein Block nach dem anderen). Grund: ab 8 gibt es keine Rücksprachen mehr, also keinen Wartegrund – und gleichzeitiges Schreiben mehrerer Blöcke in dasselbe Repo/denselben Branch erzeugt nur Konflikte.
- **Sprache:** Dieses Dokument ist der deutschsprachige Arbeitsstand. Alle tatsächlichen Artefakte (Agents, Hooks, Skills, `state.json`, `.c4`, `knowledge.md`, ADRs) werden in **Englisch** geschrieben; Bezeichner und Feldnamen sind hier bereits englisch.

## Zonen

| Zone | Schritte | Scope |
|---|---|---|
| Intake | 1–5 | Einmal pro Ticket, strikt sequenziell |
| Blocks | 6–9 | Pro Themenblock; 6–7 parallel möglich, 8–9 sequenziell |
| Delivery | 10–12 | Einmal pro Ticket, erst wenn alle Blöcke abgeschlossen sind |

---

## 1. Kontext sammeln

### 1.1. Ticket mit Kommentaren lesen
#### 1.1.1. (wenn vorhanden) Verwandte Tickets lesen (Epics, Meilensteine, etc.)
### 1.2. (wenn vorhanden) Pull Request mit Review-Kommentaren lesen
### 1.3. (wenn vorhanden) zusammenhängende Komponenten aus dem LikeC4-Modell (Ist-Zustand) lesen
### 1.4. (wenn vorhanden) betroffenen Code lesen

## 2. Das Gelesene verstehen

### 2.1. Fachliche Ziele definieren
Was soll am Ende funktionieren, neu oder besser sein für die Person oder das System, welche(s) mit der Anwendung interagiert?
### 2.2. Probleme definieren

## 3. Fachliche Fragen stellen
*(keine Rücksprache nötig – Fragen werden direkt beantwortet, keine gesonderte Übersicht danach nötig)*

## 4. Ticket in unabhängig planbare Themenblöcke gliedern

## 5. Wissen speichern
Bisher erarbeitetes Wissen in `knowledge.md` (Ticket-Repo) schreiben, inkl. Status (z. B. für Ziele, Probleme, offen gebliebene Fragen). Wird bei jedem Rücksprung (siehe unten) um einen Log-Eintrag ergänzt: *"PR-Feedback / Erkenntnis vom [Datum]: X führte zu Rücksprung auf Schritt Y."*

---
**Ab hier: pro Themenblock** (6–7 parallel über Blöcke hinweg möglich, 8–9 sequenziell)
---

## 6. Lösungsvorschläge sammeln

### 6.1. Im gesammelten Kontext nach vorhandenen Lösungsvorschlägen schauen
### 6.2. Entwickler nach möglichen Lösungsansätzen fragen
### 6.3. Selbst überlegen und recherchieren

## 7. Architektur & Design festlegen

### 7.0. Ist-Abgleich, falls Themenblock/Ticket schon länger läuft oder ein bestehender Soll-Branch weiterverwendet wird
Prüfen, ob sich der Ist-Zustand (main im Ticket-Repo) seit Beginn geändert hat (z. B. weil jemand anderes zwischenzeitlich etwas an denselben Komponenten gebaut hat). Bei Abweichung: Soll-Branch rebasen/anpassen, **Rücksprache**.
### 7.1. Betroffenes LikeC4-Modell im Soll-Branch (Ticket-Branch im Ticket-Repo) aktualisieren (Komponenten, Beziehungen)
Dabei werden die betroffenen Komponenten als `claimed_components` des Blocks deklariert. Überlappen sich die Claims zweier Blöcke, waren die Blöcke nicht unabhängig → Rücksprung 7→4.
### 7.2. Leere Stubs im Code anlegen (Signaturen – ohne Implementierung)
### 7.3. ADR schreiben, falls eine nicht-triviale Entscheidung zwischen mehreren echten Optionen aus Schritt 6 getroffen wurde (Kontext, verworfene Optionen, Begründung, Trade-offs)

→ **Rücksprache hier besonders kritisch**, da danach strikt gegen Stubs und LikeC4-Modell implementiert wird.

## 8. Implementierung

### 8.0. Implementierungsplan erstellen, falls nicht-trivial
Nur bei mehreren sinnvollen algorithmischen Ansätzen, komplexen Fehlerpfaden oder performance-kritischen Stellen. Betrifft ausschließlich das *Innere* der Methoden (Umsetzung), nicht den Vertrag (Signatur/Verhalten nach außen) – der steht bereits aus 7.2 fest. Kein eigenes Artefakt, dient nur der Selbstklärung.

→ Stellt sich dabei heraus, dass sich doch der Vertrag ändern muss (z. B. anderer Rückgabetyp nötig) → kein 8.0-Fall mehr, sondern regulärer Rücksprung 8→7 mit dortiger Rücksprache-Pflicht.

Strikt gegen die in 7.2 definierten Stubs und das in 7.1 definierte Modell – keine Abweichung ohne Rücksprung zu 7.

*(keine planmäßige Rücksprache)*

## 9. Verifikation
Tests, Abgleich Implementierung ↔ Stubs/LikeC4-Modell.

*(keine planmäßige Rücksprache)*

## 10. Pull Request erstellen
PR-Beschreibung enthält Links zu `knowledge.md`, ADR(s) und dem betroffenen `.c4`-View im Ticket-Repo.

*(keine planmäßige Rücksprache)*

## 11. PR-Feedback verarbeiten
### 11.1. Kommentare einzeln lesen und einordnen:
| Art des Kommentars | Wiedereinstieg bei |
|---|---|
| Reiner Implementierungs-Bug/Nit | 8 |
| Stub/Signatur oder LikeC4-Modell muss sich ändern | 7 (Rücksprache) |
| Fachliches Ziel/Problem war falsch verstanden | 2 (Rücksprache) |
| Fehlender Kontext, der in 1 übersehen wurde | 1 |
| Komplett neuer Scope, nicht Teil des ursprünglichen Tickets | kein Wiedereinstieg – Rücksprache: neues Ticket vorschlagen |

### 11.2. Ab dem ermittelten Punkt normal weiterlaufen (inkl. dortiger Rücksprache-Regeln)
### 11.3. Wieder vorwärts bis 10 – dort jetzt "bestehenden PR aktualisieren" statt "neuen PR erstellen"

## 12. Ist-Modell nach Merge synchronisieren
Ausgelöst manuell, z. B. per `/sync-architecture <ticket-id>`. **Kein automatischer Merge** – es gibt immer einen manuellen Check, da parallele Branches, die dieselben Komponenten anfassen, sich sonst überschreiben könnten, und weil sich der Ist-Zustand während der Laufzeit des Tickets bereits geändert haben kann.

### 12.1. Graphify/Codegraph auf den frisch gemergten Code anwenden → automatischer Ist-Extract
### 12.2. Abgleich: Soll-Branch (aus 7.1) vs. extrahiertes Ist
### 12.3. Bei Übereinstimmung: Entwickler bestätigt manuell → Soll-Branch-Inhalt wird neuer Ist-Stand (main)
### 12.4. Bei Abweichung: main nach dem extrahierten Ist korrigieren – **Rücksprache**, da Abweichung auf einen nicht dokumentierten Rücksprung während 8/9 hindeuten kann

---

## Rücksprung-Regeln

**Grundregel:** Ein Rücksprung zu einem Punkt reaktiviert dessen ursprüngliche Rücksprache-Pflicht – unabhängig davon, aus welcher Phase heraus zurückgesprungen wird.

**Abgrenzung kleine Korrektur vs. echter Rücksprung:** Ändert sich eine Signatur (Parameter, Rückgabetyp, welche Methoden es gibt) oder eine Beziehung im LikeC4-Modell? → echter Rücksprung. Ändert sich nur Naming oder ein interner Kommentar? → keine.

| Von | Zu | Auslöser |
|---|---|---|
| 6/7 | 2 | Fachliches Ziel/Problem war falsch verstanden oder unvollständig |
| 7 | 4 | Themenblock ist doch nicht unabhängig, muss neu geschnitten werden (u. a. automatisch erkannt bei Überlappung von `claimed_components` zweier Blöcke) |
| 8 | 7 | Stub/Signatur oder LikeC4-Modell ist falsch/unvollständig |
| 9 | 8 | Normaler Implementierungs-Bug |
| 9 | 7 | Design-Fehler, kein reiner Implementierungs-Bug |
| (PR) | 1/2/7/8 | Siehe Tabelle unter Schritt 11 |

Jeder Rücksprung wird in `knowledge.md` protokolliert (siehe Schritt 5).

---

## Artefakte

Alle Artefakte liegen im **Ticket-Repo** (nie im Code-Repo), Verknüpfung nur über Links:

| Artefakt | Ort | Lebensdauer |
|---|---|---|
| `.c4`/`.likec4`-Modell | `architecture/` im Ticket-Repo. `main` = Ist-Zustand, Ticket-Branch = Soll-Zustand | Fortlaufend, projektweit |
| `knowledge.md` | `tickets/<ticket-id>/knowledge.md` | Pro Ticket |
| `state.json` | `tickets/<ticket-id>/state.json` | Pro Ticket – maschinenlesbarer Zustand (Schritt/Status je Block, Rücksprachen, Rücksprünge, Claims, Stub-Fingerprints, `ist_base_commit`). Grundlage für Wiedereinstieg und spätere UI |
| ADR | `tickets/<ticket-id>/adr/000X-titel.md` | Pro Ticket, dauerhaft als Entscheidungshistorie |
| Code (Stubs, Implementierung, Tests) | Code-Repo | Pro Ticket → dauerhaft im Code |

## Repo-Struktur (Ticket-Repo, pro Projekt)

```
ticket-repo-<projekt>/
  architecture/
    specification.c4
    context.c4
    container-*.c4
    views.c4
  tickets/
    <ticket-id>/
      knowledge.md
      state.json
      adr/
        0001-title.md
```
