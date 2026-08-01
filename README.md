# README: Sistema Predictivo de Costos de Equipos de Construcción

## Introducción

Este ejercicio es una buena oportunidad para comprender la dinámica relacionada con la previsión presupuestaria en los proyectos del sector construcción. Al investigar mas a fondo en la literatura me he dado cuenta que la complejidad de los proyectos va mas allá de la magnitud de la obra civil y que también existen retos presupuestarios, operativos, de planificación e incluso de mercado de insumos que deben tomarse en cuenta para llevar a cabo cualquier obra de construcción. En lo que respecta a la planificación, poder contar con metodologias que reduzcan la incertidumbre ayuda significativamente a que el negocio sea rentable y sostenible en el tiempo. En este documento y en el código desarrollado hablaré indistantemente en primera o tercera persona. 

## Entendimiento del problema

Sobre la base de la presentación del caso de negocio hay varias precisiones que se derivan de su lectura. Uno de los problemas centrales del caso es la imposiblidad de la empresa de anticipar los costos de adquisición de dos tipos de equipos que se usan en campo. Se entiende que ambos equipos son necesarios de forma permanente en el proyecto para la ventana de ejecución definida.  Por otro lado, la gerencia tiene una sospecha (por cierto, bastante intuitiva) de que el precio de estos equipos estan atados o dependen directamente de la dinámica del mercado de materias primas, es decir, los insumos que se requieren para construir tales equipos. 

El planteamiento del caso nos da información importante. Al hablar de **costos de adquisición**, se puede presumir que los equipos pertenecen a la categoria de  gastos de capital (CAPEX). También, el texto informa que la empresa se encuentra en la fase de planificación de un proyecto, es decir, apenas está evaluando la viabilidad de la idea, haciendo pruebas de concepto, planificando el capital a largo plazo y determinando los planes de negocio. Es justo aquí donde la metodologia analítica para la previsión presupuestaria cobra una importancia clave.

## Objetivos

### General

El objetivo de este proyecto es desarrollar una metodología analítica que permita predecir el costo futuro de adquisición de equipos asociados directamente a la dinámica del mercado de materias primas. 

## Específicos

* Realizar un analisis descriptivo de los datos suministrados para conocer el comportamiento de las series de datos.
* Construir un modelo predictivo base para generar predicciones a corto y mediano plazo del precio de los equipos.
* Construir una aplicación sencilla integrada con un agente de IA que pueda dar respuesta a inquietudes del área de negocios.
* Plantear una arquitectura para el despliegue del modelo predictivo en la nube.

## Terminología básica

Para asegurar una correcta interpretación del modelo dentro del entorno de la ingeniería de costos, se definen los siguientes términos:

*   **CAPEX (Gastos de Capital):** Se refiere a inversiones en activos tangibles o intangibles que aportan valor económico a la empresa durante más de un año. Estos gastos incluyen la compra de maquinaria, vehículos, equipos informáticos, licencias de software perpetuas, reformas significativas en oficinas o desarrollo interno de productos tecnológicos capitalizables.
*   **OPEX (Gastos Operativos):** Gastos recurrentes del día a día para operar la empresa (ej. luz, salarios, alquiler). Se deducen completamente en el año fiscal actual.
*   **AACE (AACE International):** La Autoridad Internacional para la Gestión del Costo Total (Total Cost Management). Es el organismo que proporciona las directrices y estándares (Recommended Practices) globales para la ingeniería de costos y presupuestación.
*   **Clases del AACE:** Es el sistema de clasificación de estimaciones de costos que asocia el nivel de madurez o definición de un proyecto con una metodología de cálculo y un rango de precisión esperado. Las etapas tempranas de planeación corresponden a la **Clase 5** (0% a 2% de definición) y **Clase 4** (1% a 15% de definición), requiriendo métodos paramétricos y estocásticos.
*   **INPP (Índice Nacional de Precios Productor):** Es un indicador estadístico macroeconómico que mide las variaciones a través del tiempo de los precios de los bienes y servicios que se producen en el país para consumo interno y exportación. En este modelo, funciona como variable de control para identificar la inflación.  

## Investigación del escenario en al área de la construcción

En las fases tempranas de los proyectos (Clase 5 y 4), la previsión de los materiales, equipos, alquileres, consumibles, etc son de vital importancia ya que en función de la optimización de estos recursos podrían obtenerse mejores márgenes de ganancia. En un proyecto, cuando se trata de equipamiento como maquinarias y equipos especializados, la clasificación de tales gastos pueden darse en dos escenarios: Si el proyecto es de corto plazo (6 a 12 meses), normalmente los equipos se arriendan y se consideran como OPEX, pues al final del periodo estos equipos y maquinarias no pasarán a formar parte de los activos de la empresa. Sin embargo, si el contrato de alquiler es mayor de 12 meses o incluye una opción de compra al final, las normas contables internacionales como la IFRS 16 obligan a registrarlo en el balance general como un "activo por derecho de uso". En ese caso específico, el tratamiento contable se asemeja al CAPEX porque el activo se deprecia con el tiempo.

De acuerdo con Solís-Carcaño (2019), los equipos de construcción no tienen un costo de producción estático, sino que están definidos por una estructura de manufactura en la cual los metales y aleaciones base (acero, aluminio, cobre) tienen un gran peso en el valor final [https://www.redalyc.org/journal/467/46761359008/html/]. Por otro lado, de acuerdo con Jiménez-Rodríguez (2022), los precios de los equipos se ven afectados por un mecanismo de transmisión retardado y parcial conocido como el efecto *pass-through* (transferencia de precios). Si los metales suben de precio drásticamente en el mercado global, se generan riesgos críticos de incumplimiento en la cadena de suministro, ya que los fabricantes podrían rescindir los contratos a precio fijo para mejorar sus márgenes de ganancia [https://link.springer.com/article/10.1007/s10290-021-00425-2]. Por lo tanto, en la gestión de proyectos de construcción es una necesidad imperativa estimar y prever de manera sistemática los costos a futuro, permitiendo a los contratistas y dueños planificar el capital a largo plazo y blindar los contratos contra la inflación antes de comprometer los recursos. 

Todo lo anterior coincide con la hipótesis que plantea la gerencia del proyecto, es decir: la presunción de que el precio de los equipos está intimamente relacionado con el precio de las materias primas. Como afirma Jiménez-Rodríguez (2022), esto se debe a la transmisión de precios asociados con rezagos o retardos en el tiempo. Esta observación puede desde ya indicarnos, grosso modo, un metodologia para solucionar el problema: determinar si existe una relación de dependencia de las series históricas rezagadas del precio de materias primas con la serie histórica del precio de los equipos.

## Sobre los datos

Al realizar una inspección rápida a las fuentes de datos suministradas se observan 5 series históricas de frecuencia diaria (bussiness days: lunes a viernes): **Price_X**, **Price_Y**, **Price_Z**, **Price_Equipo1** y **Price_Equipo2**. La fecha de inicio y finalización corresponden a los dias 2010-01-04 y 2023-08-31 respectivamente.

## Condiciones iniciales o supuestos

El desarrollo del modelo parte de las siguientes premisas y adecuaciones sobre los datos disponibles:

*   **Frecuencia de datos:** La base de datos original contiene variables históricas a nivel diario (días laborables o *business days*). Para alinear estos datos con los índices macroeconómicos (INPP) y con los mecanismos contractuales de pago, los datos diarios se transforman a frecuencia mensual.
*   **Agrupamiento temporal:** Se utiliza un agrupamiento mensual con etiqueta de cierre de mes (`M`) para recrear las condiciones reales en las que se publican los índices oficiales.
*   **Procesamiento de la media:** La mensualización se hace bajo el criterio de promedio del precio ponderado por el tiempo de vigencia. Esto ayuda a la convergencia de las fluctuaciones interdiarias que se observan en los proyectos de construcción.
*   **Variables macroeconómicas:** En este ejercicio podrían o no incorporarse variables adicionales como el indice de precios al productor IPP. Sin embargo, al no tener referencia sobre la geolocalización del proyecto, incluir una serie nacional podria no alinearse con el contexto del origen de los datos. Pero se considera muy importante incluir esta variable en una iteracipon posterior.


## Metodología analítica

La estrategia analítica del modelo se compone de tres etapas principales: análisis exploratorio de las series (transformación y filtrado de ruido económico), determinación de relaciones entre la variable objetivo y las "predictoras" y la creación de un modelo estadístico de predicción.

1.  **Analisis exploratorio de las series:** En este paso lo que se hace es conocer la estructura de la serie, realizar una visualización, determinar completitud, realizar imputaciones, remuestreos, etc.
2. **Analisis de Causalidad de Granger:** Este método evalua si una serie de tiempo ayuda a predecir otra. Sin embargo, es preciso aclarar que no se trata de una causalidad real, pero sirve como marco de referencia. Esta prueba se sigue a un modelo de vectores autorregresivos VAR, los cuales no son mas que un sistema de ecuaciones multivariantes que permiten analizar la dinámica conjunta de varias series temporales, explicando cada variable por sus propios rezagos y los de las demás variables del sistema.
3.  **Modelado Predictivo con Machine Learning:** Una vez depuradas y/o elegidas las variables explicativas y eliminando el ruido, la base de datos se divide en conjuntos de entrenamiento, validación y prueba (*train/validation/test*) y se realiza un benchamarking de modelos de predicción de series de tiempo. Vale la pena aclarar dos cosas. La tentación inicial es usar modelos clásicos con ARIMA, ARIMAX, GARCH, etc, pero estos modelos quedan descartados de entrada debido a la existencia de modelos con un mayor poder predictivo y que además toman en consideración relaciones de dependencia con otras series y no únicamente su estructura propia de tendencia, variabilidad y autorregresión. Tampoco se ha querido usar modelos de deep learning como el **LSTM**, el cual ha demostrado empíricamente superar a los modelos tradicionales (como ARIMA) hasta en un 59% de exactitud al predecir series temporales de la industria de la construcción (Boge Lyu & Qianye Yin & Iris Denise Tommelein & Hanyang Liu & Karnamohit Ranka & Karthik Yeluripati & Junzhe Shi, 2025) [https://ideas.repec.org/p/arx/papers/2512.09360.html]. La justificación es que para estos últimos modelos se requiere de un gran número de datos.
En este sentido, los modelos que competirán son ElasticNet, LightGBM y Ridge.

## Predicción
Con el mejor modelo, se proyectará el comportamiento del CAPEX del equipo bajo los siguientes marcos de acción:
*   **Horizonte de corto plazo (1 a 2 meses):** Actuará como un panel de alertas tempranas para que el área de abastecimiento se anticipe a las fluctuaciones agresivas en los mercados spot y evite sobrecostos repentinos.
*   **Horizonte de mediano plazo (3 a 7 meses):** Actuará como un panel de previsión usual o ventana de ejecución mínima.
*   **Horizonte de largo plazo (8 a 16 meses):** Dictará los valores de planeación para establecer el presupuesto de inversión financiera.


## Intervalos de confianza

Al estar en fases tempranas de planeación, el modelo incorpora la incertidumbre inherente al nivel de madurez del proyecto, integrando simulaciones estocásticas basadas en los rangos recomendados por la AACE.

A las predicciones puntuales de la red LSTM se les acoplará una **Simulación de Montecarlo** para generar distribuciones probabilísticas que proyecten la variabilidad del costo de adquisición. Se establecerán tres intervalos clave orientados a la toma de decisiones con un nivel de confianza del 80%:
1.  **Escenario Optimista (Límite Inferior):** Representa una posible deflación en el costo de los insumos o una alta economía de escala. Se asocia al rango bajo típico de una estimación Clase 5 (aprox. **-20% a -50%** del valor base).
2.  **Escenario Equilibrado (Valor Base):** Es la línea de tendencia central arrojada directamente por el motor de Machine Learning, asumiendo un riesgo moderado.
3.  **Escenario Pesimista (Límite Superior):** Contempla disrupciones severas en la cadena de suministro o picos inflacionarios. Alineado al estándar de la AACE, este techo establece una reserva financiera que oscila entre un **+30% y un +100%** de incremento sobre el valor base predicho.

## Análisis Exploratorio de Datos (EDA)

A continuación se muestra la evolución comparativa de las materias primas frente a los equipos en Base 100:

![Evolución de Series Base 100](docs/img/eda_series_base100.png)

Aunque el conjunto de datos original registra observaciones diarias (días hábiles), he decidido realizar una agregación a frecuencia mensual. En la industria de la construcción, los horizontes de planificación, compras de CapEx, cronogramas de proyecto y cláusulas de reajuste de precios contractuales operan sobre ciclos mensuales. Asimismo, los costos de maquinaria pesada presentan rigidez de precios a corto plazo, por lo que el dato diario refleja principalmente ruido transaccional o feriados del mercado. Modular la serie a escala mensual captura con realismo el ciclo contractual de la construcción y mejora sustancialmente la señal predictiva del modelo para el horizonte de toma de decisiones de la gerencia.

![Evolución de Series Base 100](docs/img/eda_series_base100_mes.png)

Al menos en la inspección visual, las series *Price_Z* y *Price_Equipo2* y *Price_Y* y *Price_Equipo1* parecen ser idénticas entre si (o al menos parecen estar relacionadas por un factor multiplicativo en la escala). Este efecto visual podria indicar que estan correlacionadas. Sin embargo, no seria correcto decir que una explica a la otra ya que en el fondo podria tratarse de correlación espuria. Un tratamiento correcto para determinar tal relación es realizando pruebas de estacionariedad, causalidad (como la de Granger) u observando las series diferenciadas. 

# Pruebas de estacionariedad y causalidad

En esta sección voy a realizar algunas pruebas iniciales que permitirán dilucidar las posibles relaciones entre las variables.
En series financieras y de precios (como es este ejercicio), lo normal es que tengan raíz unitaria $I(1)$. Esto simplemente significa si la serie es volatil o no, es decir, si su media y varianza y autocorrelación se mantienen constantes en el tiempo o no.
Primero probaré en niveles (empezar con la serie cruda) y, si no se rechaza $H_0$ (serie no estacionaria), aplicaré primera diferencia logarítmica (tasas de crecimiento / retornos), que suele estabilizar tanto la media como la varianza. El test usual en este caso es el Test de Dickey-Fuller.