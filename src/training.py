"""utils to finetune embedding model on patents rejected by uspto"""



def train_embedding_model(train_dataset, embedder):
    """Train the embedding model on the patents rejected by USPTO."""
    # Train the embedding model on the training dataset
    embedder.train(train_dataset)
    