# Contributing a model

1. Confirm the exact official SKU and normalize it to the model filename.
2. Add one official evidence record with URL, publisher, retrieval date and a
   short normalized evidence note.
3. Add the static model definition. Do not add live state or collection
   commands.
4. Add runtime aliases only with a separate sanitized evidence record. Mark
   them `candidate` until the qualification bar is met.
5. Run validation, regenerate the checked-in index, build twice and run tests.
6. Review the generated diff and the secret scan before opening a change.

Do not edit `generated/catalog-index.json` manually. Do not add a runtime
dependency on GitHub or a network request to consume this catalog.
