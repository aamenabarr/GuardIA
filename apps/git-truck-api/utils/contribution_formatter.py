#!/usr/bin/env python3
"""
Formateador de archivos de contribuciones para análisis con IA
Convierte archivos JSON de contribuciones en resúmenes estructurados y legibles
"""

import json
import argparse
from datetime import datetime
from typing import Dict, Optional
from collections import defaultdict, Counter
import os


class ContributionFormatter:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.data = self._load_data()
        self.stats = self._calculate_stats()
    
    def _load_data(self) -> Dict:
        """Carga el archivo JSON de contribuciones"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Archivo no encontrado: {self.input_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error al parsear JSON: {e}")
    
    def _calculate_stats(self) -> Dict:
        """Calcula estadísticas generales del proyecto"""
        stats = {
            'total_files': 0,
            'total_size_bytes': 0,
            'total_commits': 0,
            'authors': Counter(),
            'file_types': Counter(),
            'directories': Counter(),
            'languages': Counter(),
            'last_changes': [],
            'biggest_files': [],
            'most_changed_files': [],
            'binary_files': 0
        }
        
        def traverse_tree(node, path=""):
            if node.get('type') == 'blob':
                stats['total_files'] += 1
                stats['total_size_bytes'] += node.get('sizeInBytes', 0)
                stats['total_commits'] += node.get('noCommits', 0)
                
                # Autores
                for author, percentage in node.get('authors', {}).items():
                    stats['authors'][author] += percentage
                
                # Tipos de archivo
                file_ext = os.path.splitext(node.get('name', ''))[-1].lower()
                if file_ext:
                    stats['file_types'][file_ext] += 1
                    # Mapeo de extensiones a lenguajes
                    lang_map = {
                        '.ts': 'TypeScript', '.tsx': 'TypeScript',
                        '.js': 'JavaScript', '.jsx': 'JavaScript',
                        '.py': 'Python', '.json': 'JSON',
                        '.css': 'CSS', '.scss': 'SCSS',
                        '.html': 'HTML', '.md': 'Markdown',
                        '.yml': 'YAML', '.yaml': 'YAML',
                        '.sql': 'SQL', '.sh': 'Shell'
                    }
                    if file_ext in lang_map:
                        stats['languages'][lang_map[file_ext]] += 1
                
                # Directorios
                dir_path = os.path.dirname(path)
                if dir_path:
                    stats['directories'][dir_path] += 1
                
                # Archivos binarios
                if node.get('isBinary', False):
                    stats['binary_files'] += 1
                
                # Últimos cambios
                last_change = node.get('lastChangeEpoch', 0)
                if last_change:
                    stats['last_changes'].append({
                        'file': path,
                        'timestamp': last_change,
                        'date': datetime.fromtimestamp(last_change).strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                # Archivos más grandes
                stats['biggest_files'].append({
                    'file': path,
                    'size': node.get('sizeInBytes', 0),
                    'size_kb': round(node.get('sizeInBytes', 0) / 1024, 2)
                })
                
                # Archivos más cambiados
                stats['most_changed_files'].append({
                    'file': path,
                    'commits': node.get('noCommits', 0)
                })
            
            elif node.get('type') == 'tree':
                for child in node.get('children', []):
                    child_path = f"{path}/{child.get('name', '')}" if path else child.get('name', '')
                    traverse_tree(child, child_path)
        
        if 'simplifiedTree' in self.data:
            traverse_tree(self.data['simplifiedTree'])
        
        # Ordenar listas
        stats['last_changes'].sort(key=lambda x: x['timestamp'], reverse=True)
        stats['biggest_files'].sort(key=lambda x: x['size'], reverse=True)
        stats['most_changed_files'].sort(key=lambda x: x['commits'], reverse=True)
        
        return stats
    
    def _format_size(self, bytes_size: int) -> str:
        """Convierte bytes a formato legible"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
    
    def _get_project_structure(self) -> str:
        """Genera un árbol visual de la estructura del proyecto"""
        structure = []
        
        def build_tree(node, prefix="", is_last=True):
            if node.get('type') in ['tree', 'blob']:
                name = node.get('name', 'unknown')
                connector = "└── " if is_last else "├── "
                
                # Información adicional para archivos
                extra_info = ""
                if node.get('type') == 'blob':
                    size = self._format_size(node.get('sizeInBytes', 0))
                    commits = node.get('noCommits', 0)
                    extra_info = f" ({size}, {commits} commits)"
                    if node.get('isBinary', False):
                        extra_info += " [BINARY]"
                
                structure.append(f"{prefix}{connector}{name}{extra_info}")
                
                if node.get('type') == 'tree' and node.get('children'):
                    children = node.get('children', [])
                    for i, child in enumerate(children):
                        is_child_last = i == len(children) - 1
                        child_prefix = prefix + ("    " if is_last else "│   ")
                        build_tree(child, child_prefix, is_child_last)
        
        if 'simplifiedTree' in self.data:
            build_tree(self.data['simplifiedTree'])
        
        return "\n".join(structure)
    
    def _get_author_analysis(self) -> str:
        """Análisis detallado de contribuciones por autor"""
        analysis = []
        
        # Estadísticas detalladas por autor
        author_stats = defaultdict(lambda: {
            'files_touched': 0,
            'files_owned': 0,  # Archivos donde es autor principal (100%)
            'files_shared': 0,  # Archivos compartidos con otros
            'total_lines': 0,
            'commits': set(),
            'file_types': Counter(),
            'directories': Counter(),
            'file_sizes': [],
            'ownership_percentage': [],
            'recent_files': [],
            'biggest_contributions': [],
            'most_changed_files': [],
            'languages_expertise': Counter()
        })
        
        def analyze_authors(node, path=""):
            if node.get('type') == 'blob':
                file_size = node.get('sizeInBytes', 0)
                file_commits = node.get('noCommits', 0)
                last_change = node.get('lastChangeEpoch', 0)
                
                # Autores principales con porcentajes
                authors_in_file = node.get('authors', {})
                for author, percentage in authors_in_file.items():
                    author_stats[author]['files_touched'] += 1
                    author_stats[author]['ownership_percentage'].append(percentage)
                    author_stats[author]['file_sizes'].append(file_size)
                    
                    # Determinar si es propietario único o compartido
                    if percentage == 100:
                        author_stats[author]['files_owned'] += 1
                    else:
                        author_stats[author]['files_shared'] += 1
                    
                    # Archivos recientes (últimos 30 días aprox)
                    if last_change > 1700000000:  # Timestamp reciente aproximado
                        author_stats[author]['recent_files'].append({
                            'file': path,
                            'timestamp': last_change,
                            'size': file_size,
                            'commits': file_commits
                        })
                
                # Autores históricos con líneas exactas
                historical_authors = node.get('unionedAuthors', {}).get('HISTORICAL', {})
                for author, lines in historical_authors.items():
                    author_stats[author]['total_lines'] += lines
                    
                    # Contribuciones más grandes
                    author_stats[author]['biggest_contributions'].append({
                        'file': path,
                        'lines': lines,
                        'size': file_size,
                        'commits': file_commits
                    })
                
                # Commits únicos por autor
                commits_in_file = node.get('commits', [])
                for author in authors_in_file.keys():
                    for commit in commits_in_file:
                        author_stats[author]['commits'].add(commit)
                
                # Análisis de tipos de archivo y lenguajes
                file_ext = os.path.splitext(node.get('name', ''))[-1].lower()
                dir_path = os.path.dirname(path)
                
                lang_map = {
                    '.ts': 'TypeScript', '.tsx': 'TypeScript',
                    '.js': 'JavaScript', '.jsx': 'JavaScript',
                    '.py': 'Python', '.json': 'JSON',
                    '.css': 'CSS', '.scss': 'SCSS',
                    '.html': 'HTML', '.md': 'Markdown',
                    '.yml': 'YAML', '.yaml': 'YAML',
                    '.sql': 'SQL', '.sh': 'Shell'
                }
                
                for author in authors_in_file.keys():
                    if file_ext:
                        author_stats[author]['file_types'][file_ext] += 1
                        if file_ext in lang_map:
                            author_stats[author]['languages_expertise'][lang_map[file_ext]] += 1
                    if dir_path:
                        author_stats[author]['directories'][dir_path] += 1
                    
                    # Archivos más cambiados por autor
                    if file_commits > 1:
                        author_stats[author]['most_changed_files'].append({
                            'file': path,
                            'commits': file_commits,
                            'size': file_size
                        })
            
            elif node.get('type') == 'tree':
                for child in node.get('children', []):
                    child_path = f"{path}/{child.get('name', '')}" if path else child.get('name', '')
                    analyze_authors(child, child_path)
        
        if 'simplifiedTree' in self.data:
            analyze_authors(self.data['simplifiedTree'])
        
        # Procesar y ordenar datos
        for author in author_stats:
            # Ordenar contribuciones por tamaño
            author_stats[author]['biggest_contributions'].sort(key=lambda x: x['lines'], reverse=True)
            author_stats[author]['most_changed_files'].sort(key=lambda x: x['commits'], reverse=True)
            author_stats[author]['recent_files'].sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Formatear análisis detallado
        total_lines_all = sum(stats['total_lines'] for stats in author_stats.values())
        total_files_all = len(set().union(*[set() for stats in author_stats.values()]))
        
        analysis.append("\n## 👥 ANÁLISIS DETALLADO DE CONTRIBUCIONES\n")
        
        for author, stats in sorted(author_stats.items(), key=lambda x: x[1]['total_lines'], reverse=True):
            lines_percentage = (stats['total_lines'] / total_lines_all * 100) if total_lines_all > 0 else 0
            avg_ownership = sum(stats['ownership_percentage']) / len(stats['ownership_percentage']) if stats['ownership_percentage'] else 0
            total_file_size = sum(stats['file_sizes'])
            unique_commits = len(stats['commits'])
            
            analysis.append(f"### 👤 **{author}**")
            analysis.append(f"")
            
            # Estadísticas principales
            analysis.append(f"#### 📊 Estadísticas Generales:")
            analysis.append(f"• **Líneas de código**: {stats['total_lines']:,} líneas ({lines_percentage:.1f}% del total)")
            analysis.append(f"• **Archivos modificados**: {stats['files_touched']} archivos")
            analysis.append(f"• **Archivos propios**: {stats['files_owned']} (100% ownership)")
            analysis.append(f"• **Archivos compartidos**: {stats['files_shared']} (ownership parcial)")
            analysis.append(f"• **Commits únicos**: {unique_commits}")
            analysis.append(f"• **Tamaño total gestionado**: {self._format_size(total_file_size)}")
            analysis.append(f"• **Ownership promedio**: {avg_ownership:.1f}%")
            analysis.append(f"")
            
            # Expertise en lenguajes
            if stats['languages_expertise']:
                analysis.append(f"#### 🚀 Expertise en Lenguajes:")
                for lang, count in stats['languages_expertise'].most_common(5):
                    lang_percentage = (count / stats['files_touched'] * 100) if stats['files_touched'] > 0 else 0
                    analysis.append(f"• **{lang}**: {count} archivos ({lang_percentage:.1f}%)")
                analysis.append(f"")
            
            # Directorios principales
            if stats['directories']:
                analysis.append(f"#### 📁 Áreas de Trabajo Principales:")
                for directory, count in stats['directories'].most_common(8):
                    analysis.append(f"• **{directory}**: {count} archivos")
                analysis.append(f"")
            
            # Contribuciones más grandes
            if stats['biggest_contributions'][:5]:
                analysis.append(f"#### 🏆 Mayores Contribuciones (por líneas):")
                for i, contrib in enumerate(stats['biggest_contributions'][:5], 1):
                    analysis.append(f"{i}. **{contrib['file']}** - {contrib['lines']} líneas ({self._format_size(contrib['size'])})")
                analysis.append(f"")
            
            # Archivos más cambiados
            if stats['most_changed_files'][:5]:
                analysis.append(f"#### 🔄 Archivos Más Modificados:")
                for i, file_info in enumerate(stats['most_changed_files'][:5], 1):
                    analysis.append(f"{i}. **{file_info['file']}** - {file_info['commits']} commits")
                analysis.append(f"")
            
            # Actividad reciente
            if stats['recent_files'][:5]:
                analysis.append(f"#### ⏰ Actividad Reciente:")
                for i, recent in enumerate(stats['recent_files'][:5], 1):
                    date_str = datetime.fromtimestamp(recent['timestamp']).strftime('%Y-%m-%d')
                    analysis.append(f"{i}. **{recent['file']}** - {date_str} ({recent['commits']} commits)")
                analysis.append(f"")
            
            # Tipos de archivo preferidos
            if stats['file_types']:
                analysis.append(f"#### 🔧 Tipos de Archivo Preferidos:")
                for file_type, count in stats['file_types'].most_common(5):
                    type_percentage = (count / stats['files_touched'] * 100) if stats['files_touched'] > 0 else 0
                    analysis.append(f"• **{file_type}**: {count} archivos ({type_percentage:.1f}%)")
                analysis.append(f"")
            
            analysis.append("---\n")
        
        return "\n".join(analysis)
    
    def _get_collaboration_analysis(self) -> str:
        """Análisis de patrones de colaboración entre autores"""
        analysis = []
        collaboration_data = defaultdict(lambda: defaultdict(int))
        shared_files = defaultdict(list)
        
        def analyze_collaboration(node, path=""):
            if node.get('type') == 'blob':
                authors_in_file = node.get('authors', {})
                if len(authors_in_file) > 1:  # Archivo compartido
                    authors_list = list(authors_in_file.keys())
                    for i, author1 in enumerate(authors_list):
                        for author2 in authors_list[i+1:]:
                            collaboration_data[author1][author2] += 1
                            collaboration_data[author2][author1] += 1
                            shared_files[f"{author1} & {author2}"].append({
                                'file': path,
                                'author1_ownership': authors_in_file[author1],
                                'author2_ownership': authors_in_file[author2],
                                'size': node.get('sizeInBytes', 0),
                                'commits': node.get('noCommits', 0)
                            })
            
            elif node.get('type') == 'tree':
                for child in node.get('children', []):
                    child_path = f"{path}/{child.get('name', '')}" if path else child.get('name', '')
                    analyze_collaboration(child, child_path)
        
        if 'simplifiedTree' in self.data:
            analyze_collaboration(self.data['simplifiedTree'])
        
        if collaboration_data:
            analysis.append("\n## 🤝 ANÁLISIS DE COLABORACIÓN\n")
            
            # Pares de colaboración más frecuentes
            collaboration_pairs = []
            for author1, collaborations in collaboration_data.items():
                for author2, count in collaborations.items():
                    if author1 < author2:  # Evitar duplicados
                        collaboration_pairs.append((author1, author2, count))
            
            collaboration_pairs.sort(key=lambda x: x[2], reverse=True)
            
            if collaboration_pairs:
                analysis.append("### 👥 Colaboraciones Más Frecuentes:")
                for author1, author2, count in collaboration_pairs[:5]:
                    analysis.append(f"• **{author1} & {author2}**: {count} archivos compartidos")
                
                # Detalles de archivos compartidos
                analysis.append("\n### 📄 Archivos Colaborativos Destacados:")
                for pair_key, files in shared_files.items():
                    if len(files) > 0:
                        analysis.append(f"\n#### {pair_key}:")
                        # Ordenar por tamaño o importancia
                        files.sort(key=lambda x: x['size'], reverse=True)
                        for i, file_info in enumerate(files[:3], 1):
                            ownership_info = f"({file_info['author1_ownership']}% / {file_info['author2_ownership']}%)"
                            analysis.append(f"{i}. **{file_info['file']}** {ownership_info} - {self._format_size(file_info['size'])}")
        
        return "\n".join(analysis)
    
    def generate_summary(self) -> str:
        """Genera el resumen completo formateado para IA"""
        project_name = self.data.get('simplifiedTree', {}).get('name', 'Proyecto')
        
        summary = f"""
# 📋 ANÁLISIS DE CONTRIBUCIONES: {project_name.upper()}

## 📊 ESTADÍSTICAS GENERALES
• **Total de archivos**: {self.stats['total_files']:,}
• **Tamaño total**: {self._format_size(self.stats['total_size_bytes'])}
• **Total de commits**: {self.stats['total_commits']:,}
• **Archivos binarios**: {self.stats['binary_files']}
• **Autores únicos**: {len(self.stats['authors'])}

## 🏗️ TECNOLOGÍAS Y LENGUAJES
"""
        
        if self.stats['languages']:
            summary += "### Lenguajes de programación:\n"
            for lang, count in self.stats['languages'].most_common():
                percentage = (count / self.stats['total_files']) * 100
                summary += f"• **{lang}**: {count} archivos ({percentage:.1f}%)\n"
        
        if self.stats['file_types']:
            summary += "\n### Tipos de archivo más comunes:\n"
            for ext, count in self.stats['file_types'].most_common(10):
                summary += f"• **{ext}**: {count} archivos\n"
        
        # Análisis de contribuciones (sección principal)
        summary += self._get_author_analysis()
        
        # Análisis de colaboración
        summary += self._get_collaboration_analysis()
        
        summary += f"""
## 📊 COMPARATIVA ENTRE AUTORES

### Distribución de Trabajo:
"""
        
        # Comparativa entre autores
        author_comparison = []
        total_lines = sum(self.stats['authors'].values())
        
        for author, lines in self.stats['authors'].most_common():
            percentage = (lines / total_lines * 100) if total_lines > 0 else 0
            author_comparison.append(f"• **{author}**: {lines:,} líneas ({percentage:.1f}%)")
        
        summary += "\n".join(author_comparison)
        
        summary += f"""

### 📈 ARCHIVOS DESTACADOS (Resumen)

#### 🔥 Archivos más grandes:
"""
        
        for i, file_info in enumerate(self.stats['biggest_files'][:5], 1):
            summary += f"{i}. **{file_info['file']}** - {file_info['size_kb']} KB\n"
        
        summary += "\n#### 🔄 Archivos con más cambios:\n"
        for i, file_info in enumerate(self.stats['most_changed_files'][:5], 1):
            summary += f"{i}. **{file_info['file']}** - {file_info['commits']} commits\n"
        
        summary += f"""
## 📁 ESTRUCTURA RESUMIDA
### Directorios principales:
"""
        
        for directory, count in self.stats['directories'].most_common(8):
            summary += f"• **{directory}**: {count} archivos\n"
        
        # Análisis de arquitectura
        summary += self._analyze_architecture()
        
        return summary
    
    def _analyze_architecture(self) -> str:
        """Analiza la arquitectura del proyecto basándose en la estructura"""
        analysis = "\n## 🏛️ ANÁLISIS DE ARQUITECTURA\n\n"
        
        # Detectar patrones arquitectónicos
        patterns = []
        directories = set(self.stats['directories'].keys())
        
        # Monorepo
        if any('packages/' in d for d in directories):
            patterns.append("**Monorepo**: Estructura con múltiples paquetes")
        
        # Next.js
        if any('src/app' in d for d in directories):
            patterns.append("**Next.js App Router**: Aplicación moderna con App Directory")
        
        # Clean Architecture
        if any('domain' in d for d in directories):
            patterns.append("**Clean Architecture**: Separación de capas de dominio")
        
        # Microservicios
        if any('apps/' in d for d in directories):
            patterns.append("**Microservicios**: Múltiples aplicaciones independientes")
        
        # UI Components
        if any('components' in d for d in directories):
            patterns.append("**Component-Based**: Arquitectura basada en componentes")
        
        if patterns:
            analysis += "### Patrones arquitectónicos detectados:\n"
            for pattern in patterns:
                analysis += f"• {pattern}\n"
        
        # Tecnologías detectadas
        tech_stack = []
        files_found = [d.lower() for d in directories]
        
        if any('firebase' in f for f in files_found):
            tech_stack.append("Firebase (Autenticación/Base de datos)")
        if any('drizzle' in f for f in files_found):
            tech_stack.append("Drizzle ORM (Base de datos)")
        if any('tailwind' in f for f in files_found):
            tech_stack.append("Tailwind CSS (Estilos)")
        if any('eslint' in f for f in files_found):
            tech_stack.append("ESLint (Linting)")
        if any('typescript' in f for f in files_found) or '.ts' in self.stats['file_types']:
            tech_stack.append("TypeScript (Tipado estático)")
        
        if tech_stack:
            analysis += "\n### Stack tecnológico:\n"
            for tech in tech_stack:
                analysis += f"• {tech}\n"
        
        return analysis
    
    def save_summary(self, output_file: Optional[str] = None) -> str:
        """Guarda el resumen en un archivo"""
        if not output_file:
            base_name = os.path.splitext(self.input_file)[0]
            output_file = f"{base_name}_summary.md"
        
        summary = self.generate_summary()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Formatea archivos de contribuciones para análisis con IA"
    )
    parser.add_argument(
        'input_file',
        help='Archivo JSON de contribuciones de entrada'
    )
    parser.add_argument(
        '-o', '--output',
        help='Archivo de salida (por defecto: input_file_summary.md)'
    )
    parser.add_argument(
        '--print',
        action='store_true',
        help='Imprimir el resumen en consola además de guardarlo'
    )
    
    args = parser.parse_args()
    
    try:
        formatter = ContributionFormatter(args.input_file)
        output_file = formatter.save_summary(args.output)
        
        print(f"✅ Resumen generado exitosamente: {output_file}")
        
        if args.print:
            print("\n" + "="*50)
            print(formatter.generate_summary())
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
