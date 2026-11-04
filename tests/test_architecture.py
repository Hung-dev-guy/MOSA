"""Guard the three layer dependency direction during later feature additions."""
import ast
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def imports(path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom):
            yield node.module or ''


def test_application_has_no_http_or_presentation_dependencies():
    for path in (ROOT/'backend/application').glob('*.py'):
        for module in imports(path):
            assert not module.startswith(('flask','backend.presentation')), (path,module)
        tree=ast.parse(path.read_text(encoding='utf-8'))
        assert not any(isinstance(n,ast.Name) and n.id in {'request','session','jsonify','g'} for n in ast.walk(tree)),path


def test_infrastructure_does_not_depend_on_upper_layers():
    for path in (ROOT/'backend/data_infrastructure').rglob('*.py'):
        for module in imports(path):
            assert not module.startswith(('backend.application','backend.presentation')), (path,module)


def test_controllers_delegate_without_sql():
    for path in (ROOT/'backend/presentation/controllers').glob('*.py'):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                assert not node.value.startswith(('SELECT ','INSERT ','UPDATE ','DELETE ')),path
        assert not any(module.startswith('backend.data_infrastructure') for module in imports(path)),path


def test_routes_registered_once(app):
    seen=set()
    for rule in app.url_map.iter_rules():
        for method in rule.methods-{'HEAD','OPTIONS'}:
            identity=(rule.rule,method)
            assert identity not in seen,identity
            seen.add(identity)
