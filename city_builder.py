from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ZoneType(str, Enum):
    EMPTY = "."
    ROAD = "R"
    RESIDENTIAL = "H"
    COMMERCIAL = "C"
    INDUSTRIAL = "I"
    POWER_PLANT = "P"
    PARK = "K"


@dataclass
class BuildingSpec:
    cost: int
    maintenance: int
    jobs: int = 0
    residents_capacity: int = 0
    pollution: int = 0
    power_output: int = 0
    happiness_bonus: int = 0


SPECS: Dict[ZoneType, BuildingSpec] = {
    ZoneType.EMPTY: BuildingSpec(cost=0, maintenance=0),
    ZoneType.ROAD: BuildingSpec(cost=10, maintenance=1),
    ZoneType.RESIDENTIAL: BuildingSpec(cost=100, maintenance=2, residents_capacity=25),
    ZoneType.COMMERCIAL: BuildingSpec(cost=160, maintenance=4, jobs=20),
    ZoneType.INDUSTRIAL: BuildingSpec(cost=220, maintenance=5, jobs=30, pollution=6),
    ZoneType.POWER_PLANT: BuildingSpec(cost=500, maintenance=12, power_output=120, pollution=8),
    ZoneType.PARK: BuildingSpec(cost=80, maintenance=1, happiness_bonus=4),
}


@dataclass
class CityStats:
    tick: int
    treasury: int
    population: int
    employed: int
    job_capacity: int
    power_demand: int
    power_supply: int
    average_happiness: float


class City:
    def __init__(self, width: int = 12, height: int = 8, starting_money: int = 5000):
        self.width = width
        self.height = height
        self.grid: List[List[ZoneType]] = [
            [ZoneType.EMPTY for _ in range(width)] for _ in range(height)
        ]
        self.residents: List[List[int]] = [[0 for _ in range(width)] for _ in range(height)]

        self.tick_count = 0
        self.treasury = starting_money
        self.tax_rate = 0.10

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        out = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                out.append((nx, ny))
        return out

    def build(self, x: int, y: int, zone: ZoneType) -> bool:
        if not self.in_bounds(x, y):
            raise ValueError("Build coordinate out of bounds")
        if zone not in SPECS:
            raise ValueError("Unknown zone type")
        if self.grid[y][x] != ZoneType.EMPTY:
            return False

        cost = SPECS[zone].cost
        if self.treasury < cost:
            return False

        self.grid[y][x] = zone
        self.treasury -= cost
        return True

    def bulldoze(self, x: int, y: int) -> bool:
        if not self.in_bounds(x, y):
            raise ValueError("Bulldoze coordinate out of bounds")
        if self.grid[y][x] == ZoneType.EMPTY:
            return False

        self.grid[y][x] = ZoneType.EMPTY
        self.residents[y][x] = 0
        return True

    def _has_adjacent_road(self, x: int, y: int) -> bool:
        return any(self.grid[ny][nx] == ZoneType.ROAD for nx, ny in self.neighbors(x, y))

    def _score_residential_tile(self, x: int, y: int) -> int:
        score = 0
        if self._has_adjacent_road(x, y):
            score += 4

        for nx, ny in self.neighbors(x, y):
            zone = self.grid[ny][nx]
            if zone == ZoneType.PARK:
                score += 3
            elif zone == ZoneType.INDUSTRIAL or zone == ZoneType.POWER_PLANT:
                score -= 3
            elif zone == ZoneType.COMMERCIAL:
                score += 1
        return score

    def _calculate_power(self) -> Tuple[int, int]:
        supply = 0
        demand = 0
        for row in self.grid:
            for zone in row:
                spec = SPECS[zone]
                supply += spec.power_output
                if zone != ZoneType.EMPTY:
                    demand += 2
                    if zone in {ZoneType.RESIDENTIAL, ZoneType.COMMERCIAL, ZoneType.INDUSTRIAL}:
                        demand += 1
        return supply, demand

    def _job_capacity(self) -> int:
        cap = 0
        for row in self.grid:
            for zone in row:
                cap += SPECS[zone].jobs
        return cap

    def simulate_tick(self) -> CityStats:
        self.tick_count += 1

        power_supply, power_demand = self._calculate_power()
        power_ratio = 1.0 if power_demand == 0 else min(1.0, power_supply / power_demand)

        # population dynamics
        total_population = 0
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] != ZoneType.RESIDENTIAL:
                    continue

                cap = SPECS[ZoneType.RESIDENTIAL].residents_capacity
                current = self.residents[y][x]
                attractiveness = self._score_residential_tile(x, y)
                growth = 0

                if attractiveness >= 4:
                    growth = 3
                elif attractiveness >= 1:
                    growth = 1
                elif attractiveness <= -2:
                    growth = -2

                if power_ratio < 1.0:
                    growth -= 1

                updated = max(0, min(cap, current + growth))
                self.residents[y][x] = updated
                total_population += updated

        jobs = self._job_capacity()
        employed = min(total_population, jobs)

        # economy: taxes, business output, and upkeep
        maintenance_cost = 0
        parks_bonus = 0
        for row in self.grid:
            for zone in row:
                maintenance_cost += SPECS[zone].maintenance
                if zone == ZoneType.PARK:
                    parks_bonus += SPECS[zone].happiness_bonus

        tax_income = int(total_population * 2 * self.tax_rate)
        business_income = int(employed * 1.3)
        power_penalty = 0 if power_ratio >= 0.85 else int((0.85 - power_ratio) * 100)

        self.treasury += tax_income + business_income - maintenance_cost - power_penalty

        avg_happiness = 50.0
        if total_population > 0:
            avg_happiness += min(30, parks_bonus * 0.5)
            avg_happiness += min(15, employed / total_population * 15)
            avg_happiness -= min(20, power_penalty * 0.2)

        return CityStats(
            tick=self.tick_count,
            treasury=self.treasury,
            population=total_population,
            employed=employed,
            job_capacity=jobs,
            power_demand=power_demand,
            power_supply=power_supply,
            average_happiness=max(0.0, min(100.0, avg_happiness)),
        )

    def render(self) -> str:
        lines: List[str] = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                zone = self.grid[y][x]
                if zone == ZoneType.RESIDENTIAL and self.residents[y][x] > 0:
                    row.append(str(min(9, self.residents[y][x] // 3)))
                else:
                    row.append(zone.value)
            lines.append(" ".join(row))
        return "\n".join(lines)


def main() -> None:
    city = City(width=12, height=8)

    # Seed a small starter city
    for x in range(1, 11):
        city.build(x, 3, ZoneType.ROAD)
    city.build(1, 2, ZoneType.POWER_PLANT)
    city.build(3, 2, ZoneType.RESIDENTIAL)
    city.build(4, 2, ZoneType.RESIDENTIAL)
    city.build(5, 2, ZoneType.COMMERCIAL)
    city.build(6, 2, ZoneType.INDUSTRIAL)
    city.build(7, 2, ZoneType.PARK)

    print("=== SimCity-style city builder prototype ===")
    print("Legend: . empty, R road, H residential, C commercial, I industrial, P power, K park")
    print()

    for _ in range(12):
        stats = city.simulate_tick()
        print(f"Tick {stats.tick}")
        print(city.render())
        print(
            f"Population={stats.population}  Employed={stats.employed}/{stats.job_capacity}  "
            f"Power={stats.power_supply}/{stats.power_demand}  Happiness={stats.average_happiness:.1f}  "
            f"Treasury=${stats.treasury}"
        )
        print("-" * 72)


if __name__ == "__main__":
    main()
