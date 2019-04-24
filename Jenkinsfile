// Work-around for Jenkins not killing/removing older queued jobs
for (int i = 0; i < (BUILD_NUMBER as int); i++) {milestone()}

// What follows is the actual pipeline that we want Jenkins to go and build, along with all of the stages

pipeline {
    options {
        timeout(time: 1, unit: 'HOURS')
            timestamps()
    }

    agent none;

    stages {
        stage("Unit Testing") {
            parallel {
                stage("Python 3.7") {
                    agent {
                        dockerfile {
                            filename 'Dockerfile.jenkins'
                            additionalBuildArgs '--build-arg TAG=3.7'
                            label 'docker'
                        }
                    }
                    steps {
                        sh 'tox -e py37'
                        stash name: 'py37_coverage', includes: '.coverage.py37'
                    }
                    post {
                        always {
                            junit 'junit.xml'
                        }
                    }
                }
                stage("Python 3.6") {
                    agent {
                        dockerfile {
                            filename 'Dockerfile.jenkins'
                            additionalBuildArgs '--build-arg TAG=3.6'
                            label 'docker'
                        }
                    }
                    steps {
                        sh 'tox -e py36'
                        stash name: 'py36_coverage', includes: '.coverage.py36'
                    }
                    post {
                        always {
                            junit 'junit.xml'
                        }
                    }
                }
                stage("Python 3.5") {
                    agent {
                        dockerfile {
                            filename 'Dockerfile.jenkins'
                            additionalBuildArgs '--build-arg TAG=3.5'
                            label 'docker'
                        }
                    }
                    steps {
                        sh 'tox -e py35'
                        stash name: 'py35_coverage', includes: '.coverage.py35'
                    }
                    post {
                        always {
                            junit 'junit.xml'
                        }
                    }
                }
                stage("Python 2.7") {
                    agent {
                        dockerfile {
                            filename 'Dockerfile.jenkins'
                            additionalBuildArgs '--build-arg TAG=2.7'
                            label 'docker'
                        }
                    }
                    steps {
                        sh 'tox -e py27'
                        stash name: 'py27_coverage', includes: '.coverage.py27'
                    }
                    post {
                        always {
                            junit 'junit.xml'
                        }
                    }
                }
                stage("Linting") {
                    agent {
                        dockerfile {
                            filename 'Dockerfile.jenkins'
                            additionalBuildArgs '--build-arg TAG=3.7'
                            label 'docker'
                        }
                    }
                    steps {
                        sh 'tox -e lint'
                    }
                }
            }
        }
        stage("Coverage Reporting") {
            agent {
                dockerfile {
                    filename 'Dockerfile.jenkins'
                    additionalBuildArgs '--build-arg TAG=3.7'
                    label 'docker'
                }
            }
            steps {
                unstash 'py37_coverage'
                unstash 'py36_coverage'
                unstash 'py35_coverage'
                unstash 'py27_coverage'

                sh 'tox -e coverage'
                cobertura coberturaReportFile: 'coverage.xml'
            }
        }
        stage("Build sdist/wheel") {
            agent {
                dockerfile {
                    filename 'Dockerfile.jenkins'
                    additionalBuildArgs '--build-arg TAG=3.7'
                    label 'docker'
                }
            }
            steps {
                sh 'tox -e build'
                archiveArtifacts artifacts: 'dist/*.whl'
                archiveArtifacts artifacts: 'dist/*.tar.gz'
            }
        }

    }
}
