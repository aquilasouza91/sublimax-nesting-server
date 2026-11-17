"""
Algoritmo Genético de Nesting - Baseado no eCut
Implementação Python do algoritmo usado em C:\eCut\eCut\DLL\eCut27x64.dll
"""

import random
import math
import time
from typing import List, Dict, Tuple
from dataclasses import dataclass
from copy import deepcopy

@dataclass
class Piece:
    """Representa uma peça a ser encaixada"""
    id: str
    width: float
    height: float
    x: float = 0.0
    y: float = 0.0
    rotation: int = 0  # 0, 90, 180, 270

@dataclass
class Sheet:
    """Representa uma folha/mídia"""
    width: float
    height: float
    pieces: List[Piece]
    
    def area_used(self) -> float:
        """Calcula área utilizada"""
        if not self.pieces:
            return 0
        max_x = max(p.x + (p.height if p.rotation == 90 or p.rotation == 270 else p.width) for p in self.pieces)
        max_y = max(p.y + (p.width if p.rotation == 90 or p.rotation == 270 else p.height) for p in self.pieces)
        return max_x * max_y

class GeneticNesting:
    """
    Algoritmo Genético de Nesting
    Baseado em: C:\eCut\eCut\ini\TNesting2014Fm\preset.ini
    """
    
    def __init__(self, 
                 sheet_width: float,
                 sheet_height: float,
                 spacing: float = 2.0,
                 genetics_time: int = 10,
                 genetics_check: int = 3,
                 population_size: int = 100):
        """
        Parâmetros do eCut:
        - genetics_time: Tempo de execução (segundos)
        - genetics_check: Número de verificações
        - spacing: Distância mínima entre peças (Distance no eCut)
        """
        self.sheet_width = sheet_width
        self.sheet_height = sheet_height
        self.spacing = spacing
        self.genetics_time = genetics_time
        self.genetics_check = genetics_check
        self.population_size = population_size
        
    def run(self, pieces: List[Dict]) -> List[Dict]:
        """Executa algoritmo genético"""
        print(f"[GENETIC] Iniciando com {len(pieces)} peças")
        print(f"[GENETIC] Folha: {self.sheet_width}x{self.sheet_height}mm")
        print(f"[GENETIC] Tempo: {self.genetics_time}s, População: {self.population_size}")
        
        # Converter entrada para objetos Piece
        piece_objects = [
            Piece(id=p.get('id', f'p{i}'), width=p['width'], height=p['height'])
            for i, p in enumerate(pieces)
        ]
        
        # Inicializar população
        start_time = time.time()
        population = self._initialize_population(piece_objects)
        
        best_solution = None
        best_fitness = float('inf')
        generation = 0
        stagnation_count = 0
        
        # Evolução
        while time.time() - start_time < self.genetics_time:
            generation += 1
            
            # Avaliar população
            fitness_scores = [(self._fitness(ind), ind) for ind in population]
            fitness_scores.sort(key=lambda x: x[0])
            
            # Melhor da geração
            current_best_fitness, current_best = fitness_scores[0]
            
            if current_best_fitness < best_fitness:
                best_fitness = current_best_fitness
                best_solution = deepcopy(current_best)
                stagnation_count = 0
                print(f"[GENETIC] Gen {generation}: Fitness={best_fitness:.0f} (melhoria!)")
            else:
                stagnation_count += 1
                
            # Parar se estagnado
            if stagnation_count > 20:
                print(f"[GENETIC] Convergiu após {generation} gerações")
                break
            
            # Nova geração
            population = self._evolve(fitness_scores)
        
        print(f"[GENETIC] Concluído: {generation} gerações em {time.time() - start_time:.1f}s")
        print(f"[GENETIC] Melhor fitness: {best_fitness:.0f}")
        
        # Converter para formato de saída
        return self._solution_to_output(best_solution)
    
    def _initialize_population(self, pieces: List[Piece]) -> List[List[Piece]]:
        """Cria população inicial com arranjos aleatórios"""
        population = []
        
        for _ in range(self.population_size):
            individual = []
            shuffled = pieces.copy()
            random.shuffle(shuffled)
            
            # Estratégia Bottom-Left com rotação aleatória (OTIMIZADA)
            for piece in shuffled:
                new_piece = deepcopy(piece)
                new_piece.rotation = random.choice([0, 90])
                
                # Grid search otimizado: step maior para ser mais rápido
                step = max(20, int(self.spacing * 5))  # Step adaptativo maior
                
                # Tentar posicionar
                placed = False
                for y in range(0, int(self.sheet_height), step):
                    for x in range(0, int(self.sheet_width), step):
                        new_piece.x = x
                        new_piece.y = y
                        
                        if self._is_valid_position(new_piece, individual):
                            individual.append(new_piece)
                            placed = True
                            break
                    if placed:
                        break
                        
            population.append(individual)
        
        return population
    
    def _is_valid_position(self, piece: Piece, placed: List[Piece]) -> bool:
        """Verifica se posição é válida"""
        # Dimensões considerando rotação
        w = piece.height if piece.rotation == 90 else piece.width
        h = piece.width if piece.rotation == 90 else piece.height
        
        # Verifica limites da folha
        if piece.x + w > self.sheet_width or piece.y + h > self.sheet_height:
            return False
        
        # Verifica colisão com outras peças
        for other in placed:
            ow = other.height if other.rotation == 90 else other.width
            oh = other.width if other.rotation == 90 else other.height
            
            # Bounding box com spacing
            if not (piece.x + w + self.spacing <= other.x or
                    piece.x >= other.x + ow + self.spacing or
                    piece.y + h + self.spacing <= other.y or
                    piece.y >= other.y + oh + self.spacing):
                return False
        
        return True
    
    def _fitness(self, individual: List[Piece]) -> float:
        """
        Calcula fitness (menor é melhor)
        Similar ao eCut: área utilizada + penalidades
        """
        if not individual:
            return float('inf')
        
        # Área utilizada
        max_x = max(p.x + (p.height if p.rotation == 90 else p.width) for p in individual)
        max_y = max(p.y + (p.width if p.rotation == 90 else p.height) for p in individual)
        area_used = max_x * max_y
        
        # Penalidade por peças não colocadas
        penalty = (len(individual) - len(individual)) * 100000
        
        # Penalidade por distribuição não compacta
        compactness_penalty = (max_x + max_y) * 10
        
        return area_used + penalty + compactness_penalty
    
    def _evolve(self, fitness_scores: List[Tuple[float, List[Piece]]]) -> List[List[Piece]]:
        """Cria nova geração via seleção, crossover e mutação"""
        new_population = []
        
        # Elitismo: manter os 10% melhores
        elite_count = self.population_size // 10
        for i in range(elite_count):
            new_population.append(deepcopy(fitness_scores[i][1]))
        
        # Gerar restante via crossover e mutação
        while len(new_population) < self.population_size:
            # Seleção por torneio
            parent1 = self._tournament_selection(fitness_scores)
            parent2 = self._tournament_selection(fitness_scores)
            
            # Crossover
            child = self._crossover(parent1, parent2)
            
            # Mutação
            if random.random() < 0.2:  # 20% chance
                child = self._mutate(child)
            
            new_population.append(child)
        
        return new_population
    
    def _tournament_selection(self, fitness_scores: List[Tuple[float, List[Piece]]]) -> List[Piece]:
        """Seleção por torneio (escolhe melhor de N aleatórios)"""
        tournament_size = 5
        tournament = random.sample(fitness_scores, min(tournament_size, len(fitness_scores)))
        return min(tournament, key=lambda x: x[0])[1]
    
    def _crossover(self, parent1: List[Piece], parent2: List[Piece]) -> List[Piece]:
        """Combina dois pais (média de posições)"""
        child = []
        
        for i in range(min(len(parent1), len(parent2))):
            new_piece = deepcopy(parent1[i])
            new_piece.x = (parent1[i].x + parent2[i].x) / 2
            new_piece.y = (parent1[i].y + parent2[i].y) / 2
            new_piece.rotation = random.choice([parent1[i].rotation, parent2[i].rotation])
            child.append(new_piece)
        
        return child
    
    def _mutate(self, individual: List[Piece]) -> List[Piece]:
        """Aplica mutação (pequenas variações)"""
        if not individual:
            return individual
        
        mutated = deepcopy(individual)
        mutation_type = random.choice(['move', 'rotate', 'swap'])
        
        if mutation_type == 'move' and mutated:
            # Move peça aleatória
            piece = random.choice(mutated)
            piece.x += random.uniform(-50, 50)
            piece.y += random.uniform(-50, 50)
            piece.x = max(0, min(piece.x, self.sheet_width))
            piece.y = max(0, min(piece.y, self.sheet_height))
            
        elif mutation_type == 'rotate' and mutated:
            # Rotaciona peça aleatória
            piece = random.choice(mutated)
            piece.rotation = 90 if piece.rotation == 0 else 0
            
        elif mutation_type == 'swap' and len(mutated) >= 2:
            # Troca posição de duas peças
            i, j = random.sample(range(len(mutated)), 2)
            mutated[i].x, mutated[j].x = mutated[j].x, mutated[i].x
            mutated[i].y, mutated[j].y = mutated[j].y, mutated[i].y
        
        return mutated
    
    def _solution_to_output(self, solution: List[Piece]) -> List[Dict]:
        """Converte solução para formato de saída"""
        if not solution:
            return []
        
        sheets = [{'index': 0, 'parts': []}]
        
        for piece in solution:
            w = piece.height if piece.rotation == 90 else piece.width
            h = piece.width if piece.rotation == 90 else piece.height
            
            sheets[0]['parts'].append({
                'id': piece.id,
                'x': float(piece.x),
                'y': float(piece.y),
                'width': float(w),
                'height': float(h),
                'rotation': piece.rotation,
                'rotated': piece.rotation == 90
            })
        
        return sheets
