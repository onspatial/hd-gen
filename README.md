# The Pattern of Life Human Mobility Simulation 





## YouTube Videos - Silent Video; Live Demonstration after Acceptance
- [Running the Graphical User Interface (GUI)](https://youtu.be/YaabLKM4mxQ)
- [Running the Headless Simulation (Data Generation)](https://youtu.be/oFIu5CAjnnc)
- [ Customize the map and generate a new map from overpass using python or QGIS ](https://youtu.be/YwuOIQZ_jBk)
- [Customize the simulation parameters](https://youtu.be/IDG7sjz5JwE)
- [Running the simulation in parallel](https://youtu.be/aBgjLmmpMd4)



## Theory and Background
This simulation models the Maslowian needs of agents (i.e., people) which drive agents’ actions and behaviors:Agents need to go home to find shelter overnight; Agents need togo to work to make money (i.e., financial balance); Agents need togo to restaurants to eat; and Agents need to go to recreational sites to meet friends and sustain their social network. Many more facets of the logic driving the behavior of agents in the Patterns of Life simulation can be found in: [Urban life: a model of people and places](https://link.springer.com/article/10.1007/s10588-021-09348-7).

## Requirements and Installation
To run the simulation, you need to have the dependencies installed. The simulation is written in Java and requires Java 8 or higher. The simulation is built using the Maven build system. To install the dependencies, you can run the [mvn.sh](mvn.sh) script. If you run the script for the first time, you need to run the script using `bash mvn.sh full` to install the local dependencies as well as the dependencies from the Maven repository. This will create a pol.jar file and store it in `jar/` directory.


## Running the Graphical User Interface (GUI)
To run the GUI of the simulation, you can run the [WorldModelUI.java](src/main/java/pol/WorldModelUI.java) file. The GUI will open and you can see the simulation running. You can also change the parameters of the simulation using the GUI. The GUI is built using the Java Swing library.
This Youtube video provides a demonstration of the GUI: [Running the Graphical User Interface (GUI)](https://youtu.be/YaabLKM4mxQ). 

## Running the Headless Simulation (Data Generation)
To run the headless simulation, you can run the [run.sh](headless/run.sh) script. The script will run the simulation and generate the data. You can modify this file to customize the simulation input, output, and parameters.

- `-Dlog.rootDirectory=data`: Specifies that the generated data will be stored in the `data` directory.

- `-Dsimulation.test=all` : Specifies that the simulation will logs all the data. This can be customized in the [ReservedLogChannels.java](src/main/java/pol/log/ReservedLogChannels.java) file.

- `-jar ../jar/pol.jar`: Specifies the path to the simulation jar file.

- `-configuration modified.properties`: This option can be used to customized the simulation's parameters. To customize the simulation and change the default parameters, you can modify the [modified.properties](headless/modified.properties) file. The simulation default parameters are stored in the [parameters.properties](parameters.properties) file.

- `-until 2880`: Specifies the number of steps the simulation will run. In this case, the simulation will run for 2880 steps. Each step is specified in the [parameters.properties](parameters.properties) file. The default step is 5 minutes. In this case the simulation will run for 2880 * 5 minutes = 14400 minutes = 240 hours = 10 days.

This Youtube video provides a demonstration of the headless simulation: [Running the Headless Simulation (Data Generation)](https://youtu.be/oFIu5CAjnnc).
    

## Customize the Map and the Simulation Parameters

### New Map:
The simulation uses a map to simulate the agents' movement. The map is stored in three different shapefiles: `buildings.shp`, `walkways.shp`, and `buildingUnits.shp`. You can generate any mpa by using the documentation on the [maps.md](documentation/maps.md) file. 
You can use the QGIS software to visualize and edit the map or we developed a python script to generate the map. The script is shown in the [maps.py](src/main/python/code/map_generation/maps.py) file. 

This is a simple example of how to generate a map using the script:
```python
output_folder = 'data/maps/test'
bounding_box = [-84.41213984, 33.72878582, -84.36418537, 33.76304255]
pqgis.generate_map(bounding_box, output_folder, new_map=True)
```
This Youtube video provides a demonstration of how to generate a new map using both QGIS and the python script: [ Customize the map and generate a new map from overpass using python or QGIS ](https://youtu.be/YwuOIQZ_jBk).

### Simulation Parameters:
The simulation parameters are stored in the [parameters.properties](parameters.properties) file. You can customize the simulation parameters by modifying this file. It is recommended to use another file to modify the parameters and keep the original file unchanged as a reference and default parameters. 

An example of the modification is shown in the [modified.properties](headless/modified.properties) file. You can use this file to customize the simulation parameters. The modified file is used in the [run.sh](headless/run.sh) script to run the simulation with the customized parameters. 
This is an example of how to modify the parameters:

```properties
numOfAgents = 500
seed = 2
maps = maps/atl/map
```

The modified file will be specified in the [run.sh](headless/run.sh) script using the `-configuration modified.properties` option.

This is the run.sh script with the modified file:
```bash
java -Dlog4j2.configurationFactory=pol.log.CustomConfigurationFactory -Dlog.rootDirectory=data -Dsimulation.test=all -jar ../jar/pol.jar -configuration modified.properties -until 2880
```

This Youtube video provides a demonstration of how to customize the simulation parameters: [Customize the simulation parameters](https://youtu.be/IDG7sjz5JwE).

## Dataset Generation
After the simulation is run, the data is stored in the directory specified in the `-Dlog.rootDirectory` option. When data is generated, the simulation will split them into different files based on their size. Some logs store more features and might need to be cut from the dataset. For example, the `agentStateTable.tsv` file stores the state of each agent at each time step. This file can be very large and might need to be cut into smaller files. To generate the trajectory of each agent, we need to cut the location, time and agent ID from the `agentStateTable.tsv` file. 
This data processing can be done using the [integrate.py](src/main/python/code/data_generation/integrate.py) script. This script will generate the trajectory of each agent and store it in a new file.

## Performance Improvement and Parallelization

To improve the performance and accelerate the data generation process, we make the simulation more efficient by making some changes to the simulation code without changing the simulation logic. 

The simulation itself is not parallelized, but we can run multiple instances of the simulation in parallel to generate the data with different parameters or the same parameters.

This is an example of how to run the simulation in parallel using the [parallel.py](src/main/python/code/data_generation/parallel.py) script:

```python
input_parameters = params.get_from_json('params.init.json')
input_parameters = params.add_id_to_params(input_parameters, "input")
simulated_params = run(input_parameters, fork_join=False, check_time=100, parallel=8)
params.save_params_to_file(simulated_params, f"params.simulated.json")
print("Results Generated successfully!")
```

This Youtube video provides a demonstration of how to run the simulation in parallel: [Running the simulation in parallel](https://youtu.be/aBgjLmmpMd4).



