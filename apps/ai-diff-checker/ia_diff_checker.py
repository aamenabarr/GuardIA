import subprocess
import requests
import sys
import re
from typing import List, Dict, Tuple

def get_diff_lines(commit_hash=None):
    if commit_hash:
        cmd = ["git", "show", "--format=", commit_hash]
    else:
        cmd = ["git", "diff", "HEAD~1", "HEAD"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error obteniendo diff: {e}")
        return ""

def extract_added_lines_by_file(diff_content) -> Dict[str, List[str]]:
    files_code = {}
    current_file = None
    current_lines = []
    
    for line in diff_content.split('\n'):
        if line.startswith('diff --git'):
            if current_file and current_lines:
                files_code[current_file] = current_lines.copy()
            
            match = re.search(r'diff --git a/(.+) b/(.+)', line)
            if match:
                current_file = match.group(2)
                current_lines = []
        
        elif line.startswith('+') and not line.startswith('+++') and not line.startswith('@@'):
            added_line = line[1:]
            if added_line.strip():
                current_lines.append(added_line)
    
    if current_file and current_lines:
        files_code[current_file] = current_lines.copy()
    
    return files_code

def should_analyze_file(file_path: str) -> bool:
    code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.go', '.rs']
    return any(file_path.endswith(ext) for ext in code_extensions)

def check_with_api(code_lines: List[str], api_url: str = "http://localhost:5002") -> Tuple[int, float]:
    code = '\n'.join(code_lines)
    
    if not code.strip():
        return None, None
    
    if len(code) > 20000:
        print(f"⚠️ Código muy grande ({len(code)} caracteres), tomando muestra...")
        code = code[:20000] + "\n# ... código truncado ..."
    
    payload = {
        "input": {
            "code": code
        }
    }
    
    try:
        response = requests.post(
            f"{api_url}/predictions",
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            output = result.get('output', {})
            prediction = output.get('prediction', 0)
            probability = output.get('probability', 0.0)
            return prediction, probability
        else:
            print(f"❌ Error en API: {response.status_code}")
            return None, None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error conectando con la API: {e}")
        return None, None

def analyze_commit(commit_hash=None):
    print("🔍 Análisis de commit...")
    if commit_hash:
        print(f"📋 Commit: {commit_hash}")
    else:
        print("📋 Último commit")
    
    diff_content = get_diff_lines(commit_hash)
    if not diff_content:
        print("❌ No se pudo obtener el diff")
        return
    
    files_code = extract_added_lines_by_file(diff_content)
    
    if not files_code:
        print("ℹ️ No se encontraron líneas agregadas")
        return
    
    code_files = {f: lines for f, lines in files_code.items() if should_analyze_file(f)}
    other_files = {f: lines for f, lines in files_code.items() if not should_analyze_file(f)}
    
    print(f"📁 Total archivos modificados: {len(files_code)}")
    print(f"💻 Archivos de código: {len(code_files)}")
    print(f"📄 Otros archivos: {len(other_files)}")
    
    if not code_files:
        print("ℹ️ No se encontraron archivos de código para analizar")
        return
    
    total_prediction = 0
    total_probability = 0
    analyzed_files = 0
    
    print(f"\n🔍 Analizando {len(code_files)} archivos de código...")
    
    for file_path, lines in code_files.items():
        print(f"\n📄 {file_path} ({len(lines)} líneas)")
        
        print("   Preview:")
        for i, line in enumerate(lines[:3], 1):
            print(f"   {i}: {line[:60]}{'...' if len(line) > 60 else ''}")
        if len(lines) > 3:
            print(f"   ... y {len(lines) - 3} líneas más")
        
        prediction, probability = check_with_api(lines)
        
        if prediction is not None:
            analyzed_files += 1
            total_prediction += prediction
            total_probability += probability
            
            status = "🚨 IA" if prediction == 1 else "✅ Humano"
            print(f"   {status} - Probabilidad IA: {probability:.1%}")
        else:
            print("   ❌ Error en análisis")
    
    if analyzed_files > 0:
        avg_prediction = total_prediction / analyzed_files
        avg_probability = total_probability / analyzed_files
        
        print(f"\n{'='*50}")
        print(f"📊 RESUMEN DEL COMMIT:")
        print(f"   Archivos de código analizados: {analyzed_files}")
        print(f"   Archivos no analizados: {len(other_files)}")
        
        if avg_prediction >= 0.5:
            print(f"🚨 RESULTADO: POSIBLE CÓDIGO GENERADO POR IA")
            print(f"📊 Probabilidad promedio: {avg_probability:.1%}")
        else:
            print(f"✅ RESULTADO: CÓDIGO ESCRITO POR HUMANO")
            print(f"📊 Probabilidad IA promedio: {avg_probability:.1%}")
        
        print(f"{'='*50}")
    else:
        print("❌ No se pudo analizar ningún archivo")

def main():
    commit_hash = sys.argv[1] if len(sys.argv) > 1 else None
    analyze_commit(commit_hash)

if __name__ == "__main__":
    main()
