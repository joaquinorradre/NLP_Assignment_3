import requests
import json
import os

def run_evaluation():
    # Cargar preguntas
    with open("eval_dataset.json", "r") as f:
        dataset = json.load(f)

    k_values = [1, 3, 5]
    metrics = {k: {"hits": 0, "mrr_sum": 0} for k in k_values}
    total = len(dataset)

    print(f"Iniciando evaluación sobre {total} preguntas...\n")

    for item in dataset:
        # 1. Consultar tu API local
        response = requests.post("http://localhost:5000/query", json={"query": item['question']})
        results = response.json().get("sources", [])

        # 2. Calcular métricas para cada K
        for k in k_values:
            top_k = results[:k]
            hit_rank = 0
            for rank, res in enumerate(top_k, 1):
                if item['expected_text'].lower() in res['chunk_text'].lower():
                    hit_rank = rank
                    break
            
            if hit_rank > 0:
                metrics[k]["hits"] += 1
                metrics[k]["mrr_sum"] += (1.0 / hit_rank)

    # 3. Mostrar y guardar resultados
    final_results = {}
    print("--- RESULTADOS FINALES ---")
    for k in k_values:
        hr = metrics[k]["hits"] / total
        mrr = metrics[k]["mrr_sum"] / total
        final_results[f"hit_rate_k{k}"] = hr
        final_results[f"mrr_k{k}"] = mrr
        print(f"K={k} | Hit Rate: {hr:.2f} | MRR: {mrr:.2f}")

    # Guardar en la carpeta results como pide la tarea
    os.makedirs("results", exist_ok=True)
    with open("results/metrics.json", "w") as f:
        json.dump(final_results, f, indent=4)
    print("\nResultados guardados en results/metrics.json")

if __name__ == "__main__":
    run_evaluation()