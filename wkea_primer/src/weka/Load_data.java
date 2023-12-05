package weka;

import weka.core.*;
import weka.core.converters.CSVLoader;
import weka.filters.Filter;
import weka.filters.unsupervised.instance.Resample;
import weka.filters.unsupervised.attribute.Normalize;
import weka.filters.unsupervised.attribute.StringToNominal;


import weka.classifiers.trees.J48;


public class Load_data {
    static public void main(String[] args){
        try{
            // Load data
            CSVLoader loader = new CSVLoader();
            loader.setSource(new java.io.File("/home/mirza/Documents/IJS/naloga1/data60.csv"));
            Instances data = loader.getDataSet();

            // Drop missing values
            data.removeIf(Instance::hasMissingValue);

            // Perform random sampling
            Resample filter = new Resample();
            filter.setSeed(42);
            filter.setInputFormat(data);
            filter.setNoReplacement(false);
            filter.setSampleSizePercent(1000.0 / data.numInstances() * 100);
            Instances sampleData = Filter.useFilter(data, filter);

            StringToNominal string_to_nominal = new StringToNominal();
            string_to_nominal.setInputFormat(sampleData);
            StringToNominal filter1 = new StringToNominal();
            filter1.setInputFormat(data);
            Instances newData = Filter.useFilter(data, filter1);

            // Split data to train and test
            int trainingDataSize = (int) Math.round(newData.numInstances() * 0.70);
            int testDataSize = newData.numInstances() - trainingDataSize;

            Instances trainData = new Instances(newData,0,trainingDataSize);
            Instances testData = new Instances(newData,trainingDataSize,testDataSize);

            trainData.setClassIndex(trainData.numAttributes() - 1);
            testData.setClassIndex(testData.numAttributes() - 1);

            // Normalize data
            Normalize normalizeFilter = new Normalize();
            normalizeFilter.setInputFormat(trainData);

            Instances normalizedTrainData = Filter.useFilter(trainData, normalizeFilter);
            Instances normalizedTestData = Filter.useFilter(testData, normalizeFilter);

            // Define the KNN model
            J48 decisionTree = new J48();
            decisionTree.setUnpruned(true);
            decisionTree.buildClassifier(normalizedTrainData);

            System.out.println("========================");
            System.out.println("Predicting test:");
            for (int i = 0; i < normalizedTestData.numInstances(); i++) {
                double actualValue = normalizedTestData.instance(i).classValue();
                Instance newInst = normalizedTestData.instance(i);
                double pred = decisionTree.classifyInstance(newInst);
                System.out.println(actualValue + " , " + pred);
            }

        } catch (Exception e){
            e.printStackTrace();
        }
    }
}
