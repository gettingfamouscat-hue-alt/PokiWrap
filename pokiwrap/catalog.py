"""Hardcoded starter catalog of popular Poki titles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogGame:
    title: str
    url: str
    tagline: str
    accent: str


GAMES: tuple[CatalogGame, ...] = (
    CatalogGame("Subway Surfers", "https://poki.com/en/g/subway-surfers", "Endless runner", "#F97316"),
    CatalogGame("Temple Run 2", "https://poki.com/en/g/temple-run-2", "Temple escape", "#D97706"),
    CatalogGame("Moto X3M", "https://poki.com/en/g/moto-x3m", "Dirt bike stunts", "#EF4444"),
    CatalogGame("Slope", "https://poki.com/en/g/slope", "Neon downhill", "#22D3EE"),
    CatalogGame("Stickman Hook", "https://poki.com/en/g/stickman-hook", "Swing and fly", "#A78BFA"),
    CatalogGame("Drive Mad", "https://poki.com/en/g/drive-mad", "Ragdoll driving", "#F43F5E"),
    CatalogGame("Smash Karts", "https://poki.com/en/g/smash-karts", "Kart combat", "#34D399"),
    CatalogGame("Paper.io 2", "https://poki.com/en/g/paper-io-2", "Claim the map", "#60A5FA"),
    CatalogGame("Run 3", "https://poki.com/en/g/run-3", "Tunnel runner", "#818CF8"),
    CatalogGame("Vex 7", "https://poki.com/en/g/vex-7", "Stickman parkour", "#FB7185"),
    CatalogGame("Basketball Stars", "https://poki.com/en/g/basketball-stars", "1v1 hoops", "#FBBF24"),
    CatalogGame("Superhot", "https://poki.com/en/g/superhot", "Time moves with you", "#F87171"),
    CatalogGame("Fireboy & Watergirl", "https://poki.com/en/g/fireboy-and-watergirl-the-forest-temple", "Co-op temple", "#4ADE80"),
    CatalogGame("2048", "https://poki.com/en/g/2048", "Number puzzle", "#F59E0B"),
    CatalogGame("Crossy Road", "https://poki.com/en/g/crossy-road", "Hop to survive", "#2DD4BF"),
    CatalogGame("Hole.io", "https://poki.com/en/g/hole-io", "Swallow the city", "#C084FC"),
    CatalogGame("Cluster Rush", "https://poki.com/en/g/cluster-rush", "Truck parkour", "#38BDF8"),
    CatalogGame("Getaway Shootout", "https://poki.com/en/g/getaway-shootout", "Chaotic getaway", "#FB923C"),
)
