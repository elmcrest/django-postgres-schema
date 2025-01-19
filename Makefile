test:
	uv run tox

clean:
	rm -rf build dist .venv .tox build django_postgres_schema.egg-info

# release:
# 	python setup.py sdist bdist_wheel upload
