# pipeline.py

from nodes import prepare_data, train_model, score_model


def pipeline(input_data):
    # Prepare the data
    prepared_data = prepare_data(input_data)

    # Train the model
    trained_model = train_model(prepared_data)

    # Score the model
    predicted_scores = score_model(trained_model, input_data)

    # Return the predicted scores
    return predicted_scores


# Example usage:

input_data = np.array([[1, 2], [3, 4]])

predicted_scores = pipeline(input_data)

print(predicted_scores)
