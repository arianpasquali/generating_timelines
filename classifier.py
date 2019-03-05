import logging
from collections import defaultdict
from itertools import cycle

import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve, auc, f1_score, recall_score, precision_score, accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
import numpy as np

import utils

classifiers = {
    'logistic_regression': LogisticRegression(),
    'svm': SVC(class_weight='balanced', probability=True),
    'linear_svm': SVC(kernel='linear', C=0.025, class_weight='balanced', probability=True),
    'svm_rbf': SVC(gamma=2, C=1, probability=True),
    'mlp': MLPClassifier(alpha=0.01, solver='adam'),
    'rf': RandomForestClassifier(class_weight='balanced', n_estimators=800, n_jobs=-1)
}


class Classifier:
    def __init__(self, X, y, classifier_type='svm', items=None, feature_names=None, binary_class=True):
        self.X = X
        self.y = y
        self.items = items
        self.classifier_type = classifier_type
        self.classifier = classifiers[classifier_type]
        self.feature_names = feature_names
        self.binary_class = binary_class
        self.colors = cycle(['cyan', 'indigo', 'seagreen', 'yellow', 'blue', 'darkorange'])
        self.line_width = 2
        self.folds_num = 10
        # cross validation (stratified, to preserve the percentage of samples for each class)
        self.cv = StratifiedKFold(n_splits=self.folds_num, shuffle=True)

    def evaluate(self):
        logging.info('Evaluating {} classifier'.format(self.classifier_type))
        accuracy_sum = 0
        recall_sum = 0
        precision_sum = 0
        f1_sum = 0
        roc_auc_sum = 0
        fold_index = 1
        for (train_index, test_index), color in zip(self.cv.split(self.X, self.y), self.colors):
            X_train, X_test = self.X[train_index], self.X[test_index]
            y_train, y_test = self.y[train_index], self.y[test_index]
            self.train(X_train, y_train)

            y_pred = list(self.classifier.predict(X_test))  # predicted classes

            # Compute various metrics
            if self.binary_class:
                accuracy = accuracy_score(y_test, y_pred)
                accuracy_sum += accuracy
                recall = recall_score(y_test, y_pred)
                recall_sum += recall
                precision = precision_score(y_test, y_pred)
                precision_sum += precision
                f1 = f1_score(y_test, y_pred)
                f1_sum += f1
                logging.info("Accuracy: %.2f", accuracy)
                logging.info("Recall: %.2f", recall)
                logging.info("Precision: %.2f", precision)
                logging.info("F-measure: %.2f", f1)

                # Compute ROC curve and AUC
                probs = list(self.classifier.predict_proba(X_test))  # probabilities for the true class
                y_prob = np.array(probs)[:, 1]
                if len(y_test) == len(y_prob):
                    fpr, tpr, _ = roc_curve(y_test, y_prob)
                    roc_auc = auc(fpr, tpr)
                    roc_auc_sum += roc_auc
                    logging.info("AUC: %.2f", roc_auc)
                    plt.plot(fpr, tpr, lw=self.line_width, color=color,
                             label='ROC fold %d (area = %.2f)' % (fold_index, roc_auc))
            else:
                recall = recall_score(y_test, y_pred, average='macro')
                recall_sum += recall
                precision = precision_score(y_test, y_pred, average='macro')
                precision_sum += precision
                f1 = f1_score(y_test, y_pred, average='macro')
                f1_sum += f1
                logging.info("Recall: %.2f", recall)
                logging.info("Precision: %.2f", precision)
                logging.info("F-measure: %.2f", f1)

        if self.binary_class:
            logging.info("Avg. accuracy: %.2f", accuracy_sum / self.folds_num)
        logging.info("Avg. recall: %.2f", recall_sum / self.folds_num)
        logging.info("Avg. precision: %.2f", precision_sum / self.folds_num)
        logging.info("Avg. F-measure: %.2f", f1_sum / self.folds_num)
        if self.binary_class:
            if roc_auc_sum > 0:
                logging.info("Avg. AUC: %.2f", roc_auc_sum / self.folds_num)
                utils.show_roc_graph(show_legend=False)

        fold_index += 1

    def cross_validate(self):
        for (train_index, test_index), color in zip(self.cv.split(self.X, self.y), self.colors):
            # remove unknowns from the training data
            train_index = [idx for idx in train_index if self.y[idx] >= 0]
            X_train = self.X[train_index]
            y_train = self.y[train_index]
            classifier = SVC(class_weight='balanced', probability=True)
            model = classifier.fit(X_train, y_train)
            yield model, test_index

    def train(self, X_train=None, y_train=None):
        if X_train is None and y_train is None:
            X_train = self.X
            y_train = self.y
        if self.classifier_type == 'dnn':
            pass  # requires tensorflow
            # feature_columns = infer_real_valued_columns_from_input(X_train)
            # self.classifier = DNNClassifier(hidden_units=[90, 70, 60, 40, 40, 20, 10],
            #                                 optimizer=AdamOptimizer(),
            #                                 dropout=0.2,
            #                                 feature_columns=feature_columns)
            # self.classifier.fit(X_train, y_train, max_steps=1600)
        else:
            self.classifier.fit(X_train, y_train)
        return self.classifier
