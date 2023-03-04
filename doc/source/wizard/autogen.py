import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def collect_files_along_path(path: str, file_tree: dict) -> list:
    files = []
    path = tuple(path.split(os.sep))
    for i in range(len(path)):
        files += file_tree.get(path[: i + 1], [])

    # Include common modules
    common_path = ("modules", "_common") + path[2:]
    for i in range(len(common_path)):
        files += file_tree.get(common_path[: i + 1], [])

    return files


def sep_to_underscores(path):
    assert os.sep in path
    return "_".join(path.split(os.sep))


def convert_path_to_filename(path):
    return sep_to_underscores(path) + ".py"


def get_trainer_cls(example_path: str):
    framework = example_path.split(os.sep)[0]
    framework_to_trainer_cls = {
        "tf": "TensorflowTrainer",
        "torch": "TorchTrainer",
        "xgboost": "XGBoostTrainer",
    }
    return framework_to_trainer_cls[framework]


RST_TEMPLATE = """
:orphan:

{title}
{header_underline}

.. literalinclude:: {requirements_path}

.. literalinclude:: {path}

"""


def generate():
    # doc/source/wizard/include
    destination_path = Path(__file__).parent / "includes"

    examples = {}
    file_tree = {}
    for root, dirs, files in os.walk(destination_path / "modules"):
        rel_root = os.path.relpath(root, destination_path)

        path = tuple(rel_root.split(os.sep))
        file_tree[path] = [os.path.join(root, file) for file in files]

        if not dirs:
            # We're at a leaf node = this is a unique example
            # modules/tf/raydata/image -> tf/raydata/image
            unique_example_path = os.path.relpath(rel_root, "modules")
            # [tf]/raydata/image -> tf
            module = unique_example_path.split(os.sep)[0]
            if module.startswith("_"):
                continue
            examples[unique_example_path] = collect_files_along_path(
                rel_root, file_tree
            )

    environment = Environment(
        loader=FileSystemLoader(str(destination_path / "templates"))
    )
    template = environment.get_template("template.txt")

    generated_examples = []
    (destination_path / "autogenerated").mkdir(exist_ok=True)
    for example_path, files in examples.items():
        example_filename = convert_path_to_filename(example_path)

        # Build mapping from code block name -> code block
        # Ex: "train_loop_body" -> "<train_loop_body code>"
        file_contents = {}
        for file in files:
            code_block_name = file.split(os.sep)[-1].replace(".py", "")
            code_block_contents = open(file, "r").read()
            file_contents[code_block_name] = code_block_contents

        content = template.render(
            **file_contents,
            custom_train_loop="train_loop_body" in file_contents,
            trainer_cls=get_trainer_cls(example_path),
            use_ray_data="raydata" in example_path,
        )
        example_path = destination_path / "autogenerated" / example_filename
        with open(example_path, "w", encoding="utf-8") as f:
            f.write(content)
        generated_examples.append(example_path)

    # Create rst files at doc/source/wizard/*.rst
    rst_destination_path = Path(__file__).parent
    for example_path in generated_examples:
        framework, dataloading, task = example_path.name.split("_")
        title = (
            f"Distributed Training with {framework} on {task} Data "
            f"using {dataloading} for Data Loading"
        )
        rel_path = example_path.relative_to(rst_destination_path)
        rst_file_contents = RST_TEMPLATE.format(
            title=title,
            header_underline="-" * len(title),
            path=rel_path,
            requirements_path=rel_path.parent.parent
            / "requirements"
            / rel_path.name.replace(".py", ".txt"),
        )
        rst_filename = example_path.name.replace(".py", ".rst")
        with open(rst_destination_path / rst_filename, "w", encoding="utf-8") as f:
            f.write(rst_file_contents)
