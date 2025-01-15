test:
	uv run tox

clean:
	rm -rf build dist .venv django_postgres_schema.egg-info

# release:
# 	python setup.py sdist bdist_wheel upload
