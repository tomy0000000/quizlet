import argparse
import csv
import os
import random
import time
from enum import Enum
from os import PathLike

from bullet import Bullet
from tqdm import tqdm

FIELDNAMES = ["index", "word", "meaning", "status"]


class Status(int, Enum):
    NOT_LEARNED = 0
    PASS_CHOICE = 1
    LEARNED = 2


#
# Util Functions
#


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def print_progress_bar(progress: int) -> None:
    for i in tqdm(range(100000), bar_format="{bar}"):
        if i >= (progress - 1) * 10000:
            time.sleep(0.00001)
        if i == progress * 10000:
            break


#
# Data Read/Write
#


def read_vocab(filename: PathLike) -> tuple[dict, dict]:
    with open(filename, "r") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = FIELDNAMES
        raw_vocabs = list(reader)
    lengths = set([len(vocab["meaning"]) for vocab in raw_vocabs])
    vocabs: dict = {status: [] for status in Status}
    index: dict = {length: [] for length in lengths}
    for vocab in raw_vocabs:
        status = Status(int(vocab["status"]))
        vocab["status"] = status
        vocabs[status].append(vocab)
        index[len(vocab["meaning"])].append(vocab["meaning"])
    return vocabs, index


def save_vocabs(filename: PathLike, vocabs: dict) -> None:
    raw_data = [vocab.copy() for status in Status for vocab in vocabs[status]]
    for vocab in raw_data:
        vocab["status"] = vocab["status"].value
    raw_data.sort(key=lambda x: int(x["index"]))
    with open(filename, "w") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerows(raw_data)


#
# Prompt Functions
#


def ask_prompt(vocab: dict, progress: int) -> bool:
    clear()
    print_progress_bar(progress)
    answer = vocab["meaning"]
    result = input(f"{vocab['word']}: ")
    correct = bool(result == answer)
    statement = "✅ Correct:" if correct else "❌ Wrong:"
    print(f"\n{statement} {answer}")
    input("Press Enter to continue...")
    return correct


def ask_choice(vocab: dict, index: dict, progress: int) -> bool:
    clear()
    print_progress_bar(progress)
    answer = vocab["meaning"]
    choices = [answer]

    pool: list = []
    max_length = max(list(index.keys()))
    length_index = len(answer)
    # Extend the pool until it has 4 elements (one of them is the answer)
    while len(pool) < 5:
        pool.extend(index[length_index])
        length_index = (length_index + max_length - 2) % max_length + 1
        # 5 -> 4 -> 3 -> 2 -> 1 -> 5 -> 4 -> 3 -> 2 -> 1 -> ...

    # randomly select 4 elements from the pool
    while len(choices) < 4:
        require = 4 - len(choices)
        for distractor in random.choices(pool, k=require):
            if distractor not in choices:
                choices.append(distractor)
    random.shuffle(choices)

    result = Bullet(
        prompt=vocab["word"], choices=choices, bullet="👉", margin=2
    ).launch()
    correct = bool(result == answer)
    statement = "✅ Correct:" if correct else "❌ Wrong:"
    print(f"\n{statement} {answer}")
    input("Press Enter to continue...")
    return correct


#
# Session Loop Functions
#


def run_prompt_session(vocabs: dict, progress: int) -> list:
    in_this_round = []
    for i in range(5):
        if not vocabs[Status.PASS_CHOICE]:
            break
        vocab_index = random.randint(0, len(vocabs[Status.PASS_CHOICE]) - 1)
        vocab = vocabs[Status.PASS_CHOICE][vocab_index]
        in_this_round.append(vocab)
        correct = ask_prompt(vocab, progress + i)
        if correct:
            vocab["status"] = Status.LEARNED
            vocabs[Status.LEARNED].append(vocab)
            vocabs[Status.PASS_CHOICE].pop(vocab_index)

    return in_this_round


def run_choice_session(vocabs: dict, index: dict, progress: int) -> list:
    in_this_round = []
    for i in range(5):
        if not vocabs[Status.NOT_LEARNED]:
            break
        vocab_index = random.randint(0, len(vocabs[Status.NOT_LEARNED]) - 1)
        vocab = vocabs[Status.NOT_LEARNED][vocab_index]
        in_this_round.append(vocab)
        correct = ask_choice(vocab, index, progress + i)
        if correct:
            vocab["status"] = Status.PASS_CHOICE
            vocabs[Status.PASS_CHOICE].append(vocab)
            vocabs[Status.NOT_LEARNED].pop(vocab_index)

    return in_this_round


def summary(vocabs: dict) -> None:
    clear()
    print("Featured in this round:\n")
    for vocab in vocabs:
        word = vocab["word"]
        meaning = vocab["meaning"]
        gutter = " " * (40 - len(word) - len(meaning) * 2)
        print(f"{word}{gutter}{meaning}")
    input("\nPress Enter to continue...")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=str)
    args = parser.parse_args()
    vocabs, index = read_vocab(args.filename)

    try:
        while True:
            if len(vocabs[Status.NOT_LEARNED]) == 0:
                if len(vocabs[Status.PASS_CHOICE]) == 0:
                    print("All vocabs are learned!")
                    break
                in_this_round = run_prompt_session(vocabs, 0)
                in_this_round += run_prompt_session(vocabs, 0)
            elif len(vocabs[Status.PASS_CHOICE]) >= 10:
                in_this_round = run_prompt_session(vocabs, 0)
                in_this_round += run_choice_session(vocabs, index, 5)
            else:
                in_this_round = run_choice_session(vocabs, index, 0)
                if len(vocabs[Status.PASS_CHOICE]) >= 10:
                    in_this_round += run_prompt_session(vocabs, 5)
                else:
                    in_this_round += run_choice_session(vocabs, index, 5)
            summary(in_this_round)
            save_vocabs(args.filename, vocabs)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
