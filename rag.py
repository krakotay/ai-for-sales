# import openai
from typing import List
from scipy import spatial
import numpy as np
import polars as pl
from config import OPENAI_CLIENT as client, logger

DF = pl.read_parquet("embeddings.parquet")

def send_table(question: list[str], example: list[str]) -> str:
    table = ""
    table += "```markdown\n" 
    table += "| question | example |\n"
    table += "| - | - |\n"

    for q, e in zip(question, example):
        table += f"| {q} | {e} |\n"

    table += "```\n"
    return table

def generate_embeddings(texts):
    response = client.embeddings.create(input=texts, model="text-embedding-3-small")
    return [item.embedding for item in response.data]


def distances_from_embeddings(
    query_embedding: List[float],
    embeddings: List[List[float]],
    distance_metric="cosine",
) -> List[List]:
    distance_metrics = {
        "cosine": spatial.distance.cosine,
        "L1": spatial.distance.cityblock,
        "L2": spatial.distance.euclidean,
        "Linf": spatial.distance.chebyshev,
    }
    distances = [
        distance_metrics[distance_metric](query_embedding, embedding)
        for embedding in embeddings
    ]
    return distances


def find_similar(query, embeddings, questions, top_n=5, threshold=0.2):
    """
    Ищет похожие вопросы на основе эмбеддингов.

    :param query: Строка запроса.
    :param embeddings: Список эмбеддингов для всех вопросов.
    :param questions: Список всех вопросов.
    :param top_n: Максимальное количество возвращаемых результатов.
    :param threshold: Минимальный порог сходства для включения в результаты.
    :return: Список кортежей (вопрос, сходство).
    """
    emb = generate_embeddings([query])
    query_embedding = emb[0]
    similarities = distances_from_embeddings(
        query_embedding, embeddings, distance_metric="cosine"
    )

    # Для косинусного расстояния: меньшие значения означают большую схожесть
    # Поэтому сортируем по возрастанию
    sorted_indices = np.argsort(similarities)

    results = []
    count = 0
    for idx in sorted_indices:
        similarity = 1 - similarities[idx]  # Преобразуем расстояние в сходство
        if similarity >= threshold:
            results.append((questions[idx], similarity))
            count += 1
            if count >= top_n:
                break
    return results


def get_examples(query: str) -> str:
    embeddings: List[float] = DF["embeddings"]
    questions: List[str] = DF["questions"].to_list()
    similar_questions = find_similar(query, embeddings, questions, threshold=0.2)
    anwers = [i[0] for i in similar_questions]
    logger.info("\n".join(anwers))
    # examples = DF.filter(DF["questions"].is_in(anwers))["example"].to_list()
    ans_df = DF.filter(DF["questions"].is_in(anwers)).drop('embeddings')
    logger.info(ans_df)
    questions = ans_df['questions'].to_list()
    examples = ans_df['example'].to_list()
    md_table = send_table(questions, examples)
    return md_table
